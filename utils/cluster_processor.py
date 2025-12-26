"""Procesamiento de clusters y cálculo de tolerancias"""

import numpy as np
import pandas as pd

from .helpers import canon, norm_cols, pick_col, to_num_series


def assign_clusters_quantiles(series: pd.Series, k: int):
    """Asigna clusters usando cuantiles.
    Maneja el caso cuando hay valores duplicados o pocos valores únicos.
    """
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)

    # Caso especial: todos los valores son iguales o hay solo 1 valor
    if s.nunique() <= 1:
        return pd.Series(np.ones(len(s), dtype=int), index=s.index)

    # Ajustar K al número de valores únicos disponibles
    # No podemos crear más clusters que valores únicos
    k_ajustado = min(k, s.nunique())

    # Intentar usar qcut primero (divide por cuantiles)
    try:
        # Usar rank para manejar duplicados
        ranked = s.rank(method="average", ascending=True)
        labels = pd.qcut(
            ranked,
            q=k_ajustado,
            labels=range(1, k_ajustado + 1),
            duplicates="drop",
        ).astype(int)

        # Verificar que se crearon todos los clusters solicitados
        if labels.nunique() < k_ajustado:
            # Si no se crearon suficientes clusters, usar división uniforme
            bins = np.linspace(s.min(), s.max(), num=k_ajustado + 1)
            labels = pd.cut(
                s,
                bins=bins,
                labels=range(1, k_ajustado + 1),
                include_lowest=True,
            ).astype(int)

        return labels

    except ValueError:
        # Si qcut falla (por ejemplo, con valores duplicados), usar división uniforme
        bins = np.linspace(s.min(), s.max(), num=k_ajustado + 1)
        labels = pd.cut(s, bins=bins, labels=range(1, k_ajustado + 1), include_lowest=True).astype(
            int,
        )
        return labels


def enforce_monotone(vals, kind):
    """Fuerza monotonicidad en valores.
    kind='min' -> no-creciente; kind='max' -> no-decreciente
    """
    v = [np.nan if pd.isna(x) else float(x) for x in vals]
    for i in range(len(v)):
        if np.isnan(v[i]):
            v[i] = v[i - 1] if i > 0 and not np.isnan(v[i - 1]) else v[i]
    if kind == "min":
        for i in range(1, len(v)):
            if not np.isnan(v[i]) and not np.isnan(v[i - 1]):
                v[i] = min(v[i], v[i - 1])
    else:
        for i in range(1, len(v)):
            if not np.isnan(v[i]) and not np.isnan(v[i - 1]):
                v[i] = max(v[i], v[i - 1])
    first = next((x for x in v if not np.isnan(x)), np.nan)
    return [first if np.isnan(x) else x for x in v]


def weighted_quantile(values, quantile, sample_weight=None):
    """Calcula cuantil ponderado."""
    v = pd.Series(values).astype(float)
    w = (
        pd.Series(np.ones(len(v)))
        if sample_weight is None
        else pd.Series(sample_weight).astype(float)
    )
    mask = ~(v.isna() | w.isna()) & (w > 0)
    v, w = v[mask], w[mask]
    if len(v) == 0:
        return np.nan
    order = np.argsort(v.values)
    v = v.values[order]
    w = w.values[order]
    cum_w = np.cumsum(w)
    tot = cum_w[-1]
    tgt = float(quantile) * float(tot)
    idx = int(np.searchsorted(cum_w, tgt, side="left"))
    idx = min(max(idx, 0), len(v) - 1)
    return float(v[idx])


def expand_or_interpolate_q(q_list, k, descending=True):
    """Expande o interpola lista de cuantiles a longitud k."""
    if q_list is None or len(q_list) == 0:
        return None
    qs = list(q_list)
    if descending:
        qs = sorted(qs, reverse=True)
    else:
        qs = sorted(qs, reverse=False)

    if len(qs) == k:
        return qs
    if len(qs) == 1:
        return [qs[0]] * k
    if len(qs) > k:
        return qs[:k]

    # Interpolación lineal
    x_known = np.linspace(1, k, num=len(qs))
    x_full = np.arange(1, k + 1)
    y = np.interp(x_full, x_known, qs)
    return [float(v) for v in y]


def var_kind(var, max_like, min_like):
    """Determina si una variable es MIN o MAX."""
    key = canon(var)
    if key in min_like:
        return "min"
    if key in max_like:
        return "max"
    if "SUMATORIA" in key or "FIRMEZASSUPERIORES" in key or "FIRMEZASUPERIOR" in key:
        return "max"
    return "max"  # por seguridad, defectos -> tope MAX


def process_clusters(resumen_mc, tolerancias_df, cruce_df, k=5, qmin=None, qmax=None):
    """Procesa clustering y calcula tolerancias por cluster.

    Args:
        resumen_mc: DataFrame con resumen por mercado-cliente (debe tener MERCADO-CLIENTE y KILOS_ASIGNABLE)
        tolerancias_df: DataFrame con tolerancias originales
        cruce_df: DataFrame con cruce de variables
        k: Número de clusters (default: 5)
        qmin: Lista de cuantiles MIN (default: [0.9, 0.7, 0.5, 0.3, 0.1])
        qmax: Lista de cuantiles MAX (default: [0.1, 0.3, 0.5, 0.7, 0.9])

    Returns:
        dict con todos los DataFrames de resultados

    """
    # Normalizar
    res = norm_cols(resumen_mc.copy())
    tol = norm_cols(tolerancias_df.copy())
    cru = norm_cols(cruce_df.copy())

    # Validar K
    K = max(1, int(k))

    # Defaults para cuantiles
    qmin_def = [0.90, 0.70, 0.50, 0.30, 0.10]
    qmax_def = [0.10, 0.30, 0.50, 0.70, 0.90]

    qmin = expand_or_interpolate_q(qmin if qmin else qmin_def, K, descending=True)
    qmax = expand_or_interpolate_q(qmax if qmax else qmax_def, K, descending=False)

    # Seleccionar columnas de resumen
    col_mc = pick_col(res, ["MERCADO-CLIENTE", "MERCADO_CLIENTE"])
    col_kg = pick_col(res, ["KILOS_ASIGNABLE", "KILOS_ASIGNABLES"])
    res[col_kg] = pd.to_numeric(res[col_kg], errors="coerce").fillna(0.0)

    res = res[[col_mc, col_kg]].sort_values(col_kg, ascending=True).reset_index(drop=True)
    res["RANK_EXIGENCIA"] = np.arange(1, len(res) + 1)
    res["CLUSTER"] = assign_clusters_quantiles(res[col_kg], k=K)

    summary = (
        res.groupby("CLUSTER", as_index=False)
        .agg(
            CLIENTES=(col_mc, "count"),
            KG_TOTAL=(col_kg, "sum"),
            KG_MEDIANA=(col_kg, "median"),
            KG_PROMEDIO=(col_kg, "mean"),
        )
        .sort_values("CLUSTER")
    )

    # Normalizar SUMATORIA CONDICIÓN
    if "SUMATORIA CONDICIÓN" in tol.columns and "SUMATORIA CONDICION" not in tol.columns:
        tol.rename(columns={"SUMATORIA CONDICIÓN": "SUMATORIA CONDICION"}, inplace=True)

    # Detección de tipo MAX/MIN desde Cruce
    cr_map = cru.dropna(subset=["VARIABLES TOLERANCIAS", "VARIABLE DE COMPARACION"]).copy()
    cr_map["VARIABLES TOLERANCIAS"] = cr_map["VARIABLES TOLERANCIAS"].astype(str).str.strip()
    cr_map["VARIABLE DE COMPARACION"] = cr_map["VARIABLE DE COMPARACION"].astype(str).str.strip()
    mapped = cr_map[
        cr_map["VARIABLE DE COMPARACION"].str.contains(r"^\d{3}\.0__", regex=True, na=False)
    ]

    max_like = set(canon(v) for v in mapped["VARIABLES TOLERANCIAS"].unique().tolist())
    max_like |= {
        canon("SUMATORIA CONDICION"),
        canon("SUMATORIA CALIDAD"),
        canon("FIRMEZAS SUPERIORES"),
        canon("FIRMEZA SUPERIOR"),
    }
    min_like = {canon("BRIX"), canon("PORC_COLOR CUBRIMIENTO MIN"), canon("FIRMEZA INFERIOR")}

    # Join tolerancias + clusters + pesos
    col_mc_tol = pick_col(tol, ["MERCADO-CLIENTE", "MERCADO_CLIENTE"])
    tolj = tol.merge(
        res[[col_mc, col_kg, "CLUSTER"]],
        left_on=col_mc_tol,
        right_on=col_mc,
        how="left",
    )
    tolj.rename(columns={col_kg: "W"}, inplace=True)  # peso

    # Variables a procesar
    base_vars = [
        "BRIX",
        "FIRMEZA INFERIOR",
        "FIRMEZAS SUPERIORES",
        "PORC_COLOR CUBRIMIENTO MIN",
        "SUMATORIA CONDICION",
        "SUMATORIA CALIDAD",
    ]
    cr_vars = [v for v in mapped["VARIABLES TOLERANCIAS"].unique().tolist() if v in tolj.columns]
    var_rows = [v for v in base_vars if v in tolj.columns] + cr_vars
    # de-dup con orden
    seen, tmp = set(), []
    for v in var_rows:
        if canon(v) not in seen:
            seen.add(canon(v))
            tmp.append(v)
    var_rows = tmp

    # ESTRICTOS/LAXOS + FUENTES
    crit_rows, lax_rows, crit_src, lax_src = [], [], [], []

    for var in var_rows:
        kind = var_kind(var, max_like, min_like)
        rowc = {"VARIABLE": var}
        rowl = {"VARIABLE": var}
        for c in range(1, K + 1):
            ser = to_num_series(tolj.loc[tolj["CLUSTER"] == c, var])
            names = tolj.loc[tolj["CLUSTER"] == c, col_mc_tol]
            if ser.dropna().empty:
                vc = vl = np.nan
                src_c = src_l = ""
            elif kind == "min":  # crítico = MAX ; laxo = MIN
                idx_max = ser.idxmax()
                idx_min = ser.idxmin()
                vc = float(ser.loc[idx_max])
                src_c = str(names.loc[idx_max])
                vl = float(ser.loc[idx_min])
                src_l = str(names.loc[idx_min])
            else:  # crítico = MIN ; laxo = MAX
                idx_min = ser.idxmin()
                idx_max = ser.idxmax()
                vc = float(ser.loc[idx_min])
                src_c = str(names.loc[idx_min])
                vl = float(ser.loc[idx_max])
                src_l = str(names.loc[idx_max])
            rowc[f"C{c}"] = vc
            rowl[f"C{c}"] = vl
            crit_src.append({"VARIABLE": var, "CLUSTER": c, "CLIENTE": src_c, "VALOR": vc})
            lax_src.append({"VARIABLE": var, "CLUSTER": c, "CLIENTE": src_l, "VALOR": vl})
        crit_rows.append(rowc)
        lax_rows.append(rowl)

    crit_df = pd.DataFrame(crit_rows).round(2)
    lax_df = pd.DataFrame(lax_rows).round(2)
    crit_src_df = pd.DataFrame(crit_src).sort_values(["VARIABLE", "CLUSTER"]).reset_index(drop=True)
    lax_src_df = pd.DataFrame(lax_src).sort_values(["VARIABLE", "CLUSTER"]).reset_index(drop=True)

    # MONOTÓNICAS
    def make_mono(df_in):
        df = df_in.copy()
        for i, r in df.iterrows():
            kd = var_kind(r["VARIABLE"], max_like, min_like)
            vals = [r[f"C{c}"] for c in range(1, K + 1)]
            fixed = enforce_monotone(vals, kd)
            for c in range(1, K + 1):
                df.at[i, f"C{c}"] = round(fixed[c - 1], 2)
        return df

    crit_mono = make_mono(crit_df)
    lax_mono = make_mono(lax_df)

    # SUGERIDAS (cuantiles ponderados) + MONO
    def make_sugeridas_quantile(tolj_df):
        rows = []
        for var in var_rows:
            kd = var_kind(var, max_like, min_like)
            rec = {"VARIABLE": var}
            for c in range(1, K + 1):
                ser = to_num_series(tolj_df.loc[tolj_df["CLUSTER"] == c, var])
                w = pd.to_numeric(
                    tolj_df.loc[tolj_df["CLUSTER"] == c, "W"],
                    errors="coerce",
                ).fillna(0.0)
                if ser.dropna().empty:
                    rec[f"C{c}"] = np.nan
                else:
                    q = qmin[c - 1] if kd == "min" else qmax[c - 1]
                    if (w > 0).sum() == 0:
                        w = pd.Series(np.ones(len(ser)), index=ser.index)
                    rec[f"C{c}"] = round(weighted_quantile(ser, q, w), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    tol_sug = make_sugeridas_quantile(tolj)
    tol_sug_mono = make_mono(tol_sug)

    return {
        "clusters_mc": res.rename(columns={col_mc: "MERCADO-CLIENTE", col_kg: "KILOS_ASIGNABLE"}),
        "clusters_summary": summary,
        "tol_criticos": crit_df,
        "tol_laxos": lax_df,
        "tol_crit_mono": crit_mono,
        "tol_lax_mono": lax_mono,
        "tol_crit_src": crit_src_df,
        "tol_lax_src": lax_src_df,
        "tol_sugeridas": tol_sug,
        "tol_sug_mono": tol_sug_mono,
    }
