# -*- coding: utf-8 -*-
"""
cluster_strict_lax_mono_v2.py (lee ResumenMC existente, cuantiles parametrizables)
----------------------------------------------------------------------------------
Lee pesos (KILOS_ASIGNABLE) desde Asignacion_NectarinAm_por_MercadoCliente.xlsx (hoja ResumenMC)
y genera un Excel con:

- ClustersMC, Clusters_Summary
- Tol_Criticos, Tol_Laxos
- Tol_Crit_Mono, Tol_Lax_Mono
- Tol_Crit_Src, Tol_Lax_Src
- Tol_Sugeridas  (cuantiles ponderados por KILOS_ASIGNABLE, parametrizables)
- Tol_Sug_Mono   (versión monotónica de Tol_Sugeridas)

Parámetros principales (CLI):
  --in-res      archivo con ResumenMC (default: Asignacion_NectarinAm_por_MercadoCliente.xlsx)
  --in-tol      Tolerancia_NectarinAm.xlsx
  --in-cruce    Cruce de Variables.xlsx
  --out         Asignacion_NectarinAm_STRICT_LAX_v2.xlsx
  --clusters    K (default: 5)
  --qmin        cuantiles MIN (ej: "0.9,0.7,0.5,0.3,0.1" o "90,70,50,30,10")
  --qmax        cuantiles MAX (ej: "0.1,0.3,0.5,0.7,0.9" o "10,30,50,70,90")

Lógica por defecto si no pasas --qmin/--qmax:
  MIN:  0.90, 0.70, 0.50, 0.30, 0.10
  MAX:  0.10, 0.30, 0.50, 0.70, 0.90
"""

from pathlib import Path
import pandas as pd
import numpy as np
import re, unicodedata, argparse, sys

# ---------------- HELPERS ----------------
def norm_cols(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def canon(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().strip()
    return s.replace(" ", "").replace("_", "").replace("-", "").replace("/", "")

def to_num_series(ser: pd.Series) -> pd.Series:
    return (ser.astype(str)
            .str.replace("%","", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace("\xa0","", regex=False)
            .str.replace(r"[^0-9\.\-]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce"))

def pick_col(df, candidates):
    cmap = {canon(c): c for c in df.columns}
    for cand in candidates:
        if canon(cand) in cmap: return cmap[canon(cand)]
    for c in df.columns:
        if any(canon(cand) in canon(c) for cand in candidates): return c
    raise KeyError(f"No encontré {candidates}. Columnas: {list(df.columns)}")

def assign_clusters_quantiles(series: pd.Series, k: int):
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if s.nunique() <= 1:
        return pd.Series(np.ones(len(s), dtype=int), index=s.index)
    labels = pd.qcut(
        s.rank(method="average", ascending=True),
        q=min(k, s.nunique()),
        labels=range(1, min(k, s.nunique())+1),
        duplicates="drop"
    ).astype(int)
    if labels.nunique() < k:
        bins = np.linspace(s.min(), s.max(), num=k+1)
        labels = pd.cut(s, bins=bins, labels=range(1,k+1), include_lowest=True).astype(int)
    return labels

def enforce_monotone(vals, kind):
    # kind='min' -> no-creciente; kind='max' -> no-decreciente
    v = [np.nan if pd.isna(x) else float(x) for x in vals]
    for i in range(len(v)):
        if np.isnan(v[i]):
            v[i] = v[i-1] if i>0 and not np.isnan(v[i-1]) else v[i]
    if kind == "min":
        for i in range(1, len(v)):
            if not np.isnan(v[i]) and not np.isnan(v[i-1]): v[i] = min(v[i], v[i-1])
    else:
        for i in range(1, len(v)):
            if not np.isnan(v[i]) and not np.isnan(v[i-1]): v[i] = max(v[i], v[i-1])
    first = next((x for x in v if not np.isnan(x)), np.nan)
    return [first if np.isnan(x) else x for x in v]

def weighted_quantile(values, quantile, sample_weight=None):
    v = pd.Series(values).astype(float)
    w = pd.Series(np.ones(len(v))) if sample_weight is None else pd.Series(sample_weight).astype(float)
    mask = ~(v.isna() | w.isna()) & (w > 0)
    v, w = v[mask], w[mask]
    if len(v) == 0: return np.nan
    order = np.argsort(v.values)
    v = v.values[order]; w = w.values[order]
    cum_w = np.cumsum(w); tot = cum_w[-1]
    tgt = float(quantile) * float(tot)
    idx = int(np.searchsorted(cum_w, tgt, side="left"))
    idx = min(max(idx, 0), len(v)-1)
    return float(v[idx])

def parse_quantiles_arg(s: str):
    """
    Acepta '0.9,0.7,0.5' o '90,70,50'. Convierte a [0..1]. Ignora espacios.
    """
    if s is None: return None
    parts = [p.strip() for p in s.split(",") if p.strip()!=""]
    out = []
    for p in parts:
        try:
            x = float(p.replace("%",""))
            if x > 1.0: x = x/100.0
            x = min(max(x, 0.0), 1.0)
            out.append(x)
        except:
            continue
    return out if out else None

def expand_or_interpolate_q(q_list, k, descending=True):
    """
    Devuelve una lista de longitud k.
    - Si len==k: la devuelve tal cual.
    - Si len==1: repite el único valor.
    - Si 2<=len<k: interpola linealmente entre los puntos.
    - Si len>k: toma los primeros k.
    - descending: True si se espera tendencia decreciente C1->Ck (MIN),
                  False si creciente C1->Ck (MAX).
    """
    if q_list is None or len(q_list)==0:
        return None
    qs = list(q_list)
    if descending:
        qs = sorted(qs, reverse=True)
    else:
        qs = sorted(qs, reverse=False)

    if len(qs) == k:
        return qs
    if len(qs) == 1:
        return [qs[0]]*k
    if len(qs) > k:
        return qs[:k]

    # Interpolación lineal
    x_known = np.linspace(1, k, num=len(qs))
    x_full  = np.arange(1, k+1)
    y = np.interp(x_full, x_known, qs)
    return [float(v) for v in y]

# ---------------- MAIN ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-res", default="Asignacion_NectarinAm_por_MercadoCliente.xlsx")
    ap.add_argument("--in-tol", default="Tolerancia_NectarinAm.xlsx")
    ap.add_argument("--in-cruce", default="Cruce de Variables.xlsx")
    ap.add_argument("--out", default="Asignacion_NectarinAm_Cluster_Total.xlsx")
    ap.add_argument("--clusters", type=int, default=5)
    ap.add_argument("--qmin", default=None, help="Cuantiles MIN, ej: '0.9,0.7,0.5,0.3,0.1' o '90,70,50,30,10'")
    ap.add_argument("--qmax", default=None, help="Cuantiles MAX, ej: '0.1,0.3,0.5,0.7,0.9' o '10,30,50,70,90'")
    args = ap.parse_args()

    K = max(1, int(args.clusters))

    # Defaults si no vienen
    qmin_def = [0.90, 0.70, 0.50, 0.30, 0.10]
    qmax_def = [0.10, 0.30, 0.50, 0.70, 0.90]

    qmin_in = parse_quantiles_arg(args.qmin)
    qmax_in = parse_quantiles_arg(args.qmax)

    qmin = expand_or_interpolate_q(qmin_in if qmin_in else qmin_def, K, descending=True)
    qmax = expand_or_interpolate_q(qmax_in if qmax_in else qmax_def, K, descending=False)

    print(f"[INFO] K={K}")
    print(f"[INFO] Cuantiles MIN por cluster (C1..C{K}): {qmin}")
    print(f"[INFO] Cuantiles MAX por cluster (C1..C{K}): {qmax}")

    # ---- Load ResumenMC (ya calculado) ----
    F_RES = Path(args.in_res)
    res = pd.read_excel(F_RES, sheet_name="ResumenMC")
    res = norm_cols(res)
    col_mc = pick_col(res, ["MERCADO-CLIENTE","MERCADO_CLIENTE"])
    col_kg = pick_col(res, ["KILOS_ASIGNABLE","KILOS_ASIGNABLES"])
    res[col_kg] = pd.to_numeric(res[col_kg], errors="coerce").fillna(0.0)

    res = res[[col_mc, col_kg]].sort_values(col_kg, ascending=True).reset_index(drop=True)
    res["RANK_EXIGENCIA"] = np.arange(1, len(res)+1)
    res["CLUSTER"] = assign_clusters_quantiles(res[col_kg], k=K)

    summary = (res.groupby("CLUSTER", as_index=False)
               .agg(CLIENTES=(col_mc,"count"),
                    KG_TOTAL=(col_kg,"sum"),
                    KG_MEDIANA=(col_kg,"median"),
                    KG_PROMEDIO=(col_kg,"mean"))
               .sort_values("CLUSTER"))

    # ---- Load Tolerancias + Cruce ----
    tol  = norm_cols(pd.read_excel(Path(args.in_tol)))
    cru  = norm_cols(pd.read_excel(Path(args.in_cruce)))

    # Normaliza SUMATORIA CONDICIÓN
    if "SUMATORIA CONDICIÓN" in tol.columns and "SUMATORIA CONDICION" not in tol.columns:
        tol.rename(columns={"SUMATORIA CONDICIÓN":"SUMATORIA CONDICION"}, inplace=True)

    # Detección de tipo MAX/MIN desde Cruce (si compara con 500/600 => MAX)
    cr_map = cru.dropna(subset=["VARIABLES TOLERANCIAS","VARIABLE DE COMPARACION"]).copy()
    cr_map["VARIABLES TOLERANCIAS"] = cr_map["VARIABLES TOLERANCIAS"].astype(str).str.strip()
    cr_map["VARIABLE DE COMPARACION"] = cr_map["VARIABLE DE COMPARACION"].astype(str).str.strip()
    mapped = cr_map[cr_map["VARIABLE DE COMPARACION"].str.contains(r"^\d{3}\.0__", regex=True, na=False)]

    max_like = set(canon(v) for v in mapped["VARIABLES TOLERANCIAS"].unique().tolist())
    max_like |= {canon("SUMATORIA CONDICION"), canon("SUMATORIA CALIDAD"),
                 canon("FIRMEZAS SUPERIORES"), canon("FIRMEZA SUPERIOR")}
    min_like = {canon("BRIX"), canon("PORC_COLOR CUBRIMIENTO MIN"), canon("FIRMEZA INFERIOR")}

    def var_kind(var):
        key = canon(var)
        if key in min_like: return "min"
        if key in max_like: return "max"
        if "SUMATORIA" in key or "FIRMEZASSUPERIORES" in key or "FIRMEZASUPERIOR" in key:
            return "max"
        return "max"   # por seguridad, defectos -> tope MAX

    # Join tolerancias + clusters + pesos (W=KILOS_ASIGNABLE)
    col_mc_tol = pick_col(tol, ["MERCADO-CLIENTE","MERCADO_CLIENTE"])
    tolj = tol.merge(res[[col_mc, col_kg, "CLUSTER"]],
                     left_on=col_mc_tol, right_on=col_mc, how="left")
    tolj.rename(columns={col_kg:"W"}, inplace=True)  # peso

    # Variables a procesar (básicas + las mapeadas por Cruce que existan en TOL)
    base_vars = ["BRIX","FIRMEZA INFERIOR","FIRMEZAS SUPERIORES",
                 "PORC_COLOR CUBRIMIENTO MIN","SUMATORIA CONDICION","SUMATORIA CALIDAD"]
    cr_vars = [v for v in mapped["VARIABLES TOLERANCIAS"].unique().tolist() if v in tolj.columns]
    var_rows = [v for v in base_vars if v in tolj.columns] + cr_vars
    # de-dup con orden
    seen, tmp = set(), []
    for v in var_rows:
        if canon(v) not in seen:
            seen.add(canon(v)); tmp.append(v)
    var_rows = tmp

    # ---- ESTRICTOS/LAXOS + FUENTES ----
    crit_rows, lax_rows, crit_src, lax_src = [], [], [], []

    for var in var_rows:
        kind = var_kind(var)
        rowc = {"VARIABLE": var}; rowl = {"VARIABLE": var}
        for c in range(1, K+1):
            ser   = to_num_series(tolj.loc[tolj["CLUSTER"]==c, var])
            names = tolj.loc[tolj["CLUSTER"]==c, col_mc_tol]
            if ser.dropna().empty:
                vc = vl = np.nan; src_c = src_l = ""
            else:
                if kind == "min":   # crítico = MAX ; laxo = MIN
                    idx_max = ser.idxmax(); idx_min = ser.idxmin()
                    vc = float(ser.loc[idx_max]); src_c = str(names.loc[idx_max])
                    vl = float(ser.loc[idx_min]); src_l = str(names.loc[idx_min])
                else:               # crítico = MIN ; laxo = MAX
                    idx_min = ser.idxmin(); idx_max = ser.idxmax()
                    vc = float(ser.loc[idx_min]); src_c = str(names.loc[idx_min])
                    vl = float(ser.loc[idx_max]); src_l = str(names.loc[idx_max])
            rowc[f"C{c}"] = vc; rowl[f"C{c}"] = vl
            crit_src.append({"VARIABLE": var, "CLUSTER": c, "CLIENTE": src_c, "VALOR": vc})
            lax_src.append({"VARIABLE": var, "CLUSTER": c, "CLIENTE": src_l, "VALOR": vl})
        crit_rows.append(rowc); lax_rows.append(rowl)

    crit_df = pd.DataFrame(crit_rows).round(2)
    lax_df  = pd.DataFrame(lax_rows).round(2)
    crit_src_df = pd.DataFrame(crit_src).sort_values(["VARIABLE","CLUSTER"]).reset_index(drop=True)
    lax_src_df  = pd.DataFrame(lax_src).sort_values(["VARIABLE","CLUSTER"]).reset_index(drop=True)

    # ---- MONOTÓNICAS (estricto y laxo) ----
    def make_mono(df_in):
        df = df_in.copy()
        for i, r in df.iterrows():
            kd = var_kind(r["VARIABLE"])
            vals = [r[f"C{c}"] for c in range(1, K+1)]
            fixed = enforce_monotone(vals, kd)
            for c in range(1, K+1):
                df.at[i, f"C{c}"] = round(fixed[c-1], 2)
        return df

    crit_mono = make_mono(crit_df)
    lax_mono  = make_mono(lax_df)

    # ---- SUGERIDAS (cuantiles ponderados) + MONO ----
    # qmin: decreciente C1..Ck (MIN), qmax: creciente C1..Ck (MAX)
    def make_sugeridas_quantile(tolj_df):
        rows = []
        for var in var_rows:
            kd = var_kind(var)
            rec = {"VARIABLE": var}
            for c in range(1, K+1):
                ser = to_num_series(tolj_df.loc[tolj_df["CLUSTER"]==c, var])
                w   = pd.to_numeric(tolj_df.loc[tolj_df["CLUSTER"]==c, "W"], errors="coerce").fillna(0.0)
                if ser.dropna().empty:
                    rec[f"C{c}"] = np.nan
                else:
                    q = qmin[c-1] if kd == "min" else qmax[c-1]
                    if (w>0).sum()==0:  # si no hay pesos >0, usa pesos = 1
                        w = pd.Series(np.ones(len(ser)), index=ser.index)
                    rec[f"C{c}"] = round(weighted_quantile(ser, q, w), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    tol_sug = make_sugeridas_quantile(tolj)
    tol_sug_mono = make_mono(tol_sug)

    # ---- WRITE ----
    try:
        import xlsxwriter  # noqa
        engine = "xlsxwriter"
    except ImportError:
        engine = "openpyxl"

    OUT = Path(args.out)
    with pd.ExcelWriter(OUT, engine=engine, mode="w") as xw:
        # Clusters
        res.rename(columns={col_mc:"MERCADO-CLIENTE", col_kg:"KILOS_ASIGNABLE"}) \
           .to_excel(xw, index=False, sheet_name="ClustersMC")
        summary.to_excel(xw, index=False, sheet_name="Clusters_Summary")
        # Estrictos/Laxos
        crit_df.to_excel(xw, index=False, sheet_name="Tol_Criticos")
        lax_df.to_excel(xw, index=False, sheet_name="Tol_Laxos")
        crit_mono.to_excel(xw, index=False, sheet_name="Tol_Crit_Mono")
        lax_mono.to_excel(xw, index=False, sheet_name="Tol_Lax_Mono")
        crit_src_df.to_excel(xw, index=False, sheet_name="Tol_Crit_Src")
        lax_src_df.to_excel(xw, index=False, sheet_name="Tol_Lax_Src")
        # Sugeridas
        tol_sug.to_excel(xw, index=False, sheet_name="Tol_Sugeridas")
        tol_sug_mono.to_excel(xw, index=False, sheet_name="Tol_Sug_Mono")

    print(f"[OK] -> {OUT.resolve()}")

if __name__ == "__main__":
    main()
