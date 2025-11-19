# -*- coding: utf-8 -*-
"""
Asignación de Nectarin Amarillo por Lote y Mercado-Cliente
Fix calibre: normaliza [min,max] aunque vengan invertidos (p.ej. SUP=48, INF=88).
- Disminución 500/600: valor * (1 - %disminucion)
- BRIX, Firmeza (rango), Color mínimo, topes individuales 500/600 y Sumatorias
- Calibres 100.x NO bloquean: asigna KILOS_REAL * %CALIBRES_EN_RANGO
- Depuración: CALIBRES_DENTRO / CALIBRES_FUERA
"""

from pathlib import Path
import pandas as pd
import numpy as np
import re

# ========= CONFIG =========
BASE_DIR = Path(".")
F_NECT = BASE_DIR / "NectarinAm.xlsx"
F_TOL  = BASE_DIR / "Tolerancia_NectarinAm.xlsx"
F_DIS  = BASE_DIR / "Disminucion.xlsx"
F_CRU  = BASE_DIR / "Cruce de Variables.xlsx"
OUT_XLSX = BASE_DIR / "Asignacion_NectarinAm_por_MercadoCliente.xlsx"
CHECK_LOTE = None  # ej. 806 para crear hoja "Check_806"; None para omitir

# ========= UTILIDADES =========
def norm(s): return str(s).strip()

def pct_to_fraction(x) -> float:
    """'96,6%' -> 0.966 ; '96.6' -> 0.966 ; 0.966 -> 0.966"""
    if pd.isna(x): return 0.0
    s = str(x).strip().replace('%','').replace(',','.')
    try:
        v = float(s)
    except Exception:
        v = pd.to_numeric(x, errors='coerce')
        if pd.isna(v): return 0.0
    return v/100.0 if v > 1.0 else v

def pct_color_ge(row: pd.Series, threshold: float) -> float:
    color_bins = ['400.0__0 - 30', '400.0__30-50', '400.0__50-75', '400.0__75-100']
    bin_lower  = {'400.0__0 - 30':0, '400.0__30-50':30, '400.0__50-75':50, '400.0__75-100':75}
    acc, total = 0.0, 0.0
    for b in color_bins:
        val = row.get(b, 0.0)
        if pd.isna(val): val = 0.0
        total += val
        if bin_lower[b] >= threshold:
            acc += val
    if total > 0 and (1.0001 < total <= 100.0001):
        return acc  # ya está en %
    return (acc/total*100.0) if total > 0 else 0.0

def parse_calibre_cols(cols):
    """Devuelve dict {col_name:int_calibre} para columnas 100.0__XX"""
    cal_map = {}
    for c in cols:
        if str(c).startswith("100.0__"):
            m = re.search(r"100\.0__([0-9]+)", str(c))
            if m: cal_map[c] = int(m.group(1))
    return cal_map

def normalize_bounds(inf, sup):
    """
    Normaliza límites: devuelve (lo, hi) donde lo<=hi.
    Trata 0/NaN como 'sin restricción'.
    """
    lo = None if (pd.isna(inf) or float(inf) == 0.0) else float(inf)
    hi = None if (pd.isna(sup) or float(sup) == 0.0) else float(sup)
    if lo is None and hi is None:
        return None, None
    if lo is not None and hi is not None:
        return (min(lo, hi), max(lo, hi))
    # si solo hay uno, lo uso como único límite
    return (lo, hi)

def pct_calibres_en_rango_y_listas(row, cal_map, cal_inf, cal_sup):
    """
    Calcula % en rango y lista de calibres dentro/fuera, normalizando rangos invertidos.
    """
    lo, hi = normalize_bounds(cal_inf, cal_sup)
    sum_in, total = 0.0, 0.0
    dentro, fuera = [], []
    for col, cal in cal_map.items():
        val = row.get(col, 0.0)
        val = 0.0 if pd.isna(val) else float(val)
        total += val
        ok_lo = True if lo is None else (cal >= lo)
        ok_hi = True if hi is None else (cal <= hi)
        if ok_lo and ok_hi:
            sum_in += val
            if val > 0: dentro.append(cal)
        else:
            if val > 0: fuera.append(cal)

    # si los 100.x ya están en %, devuelvo sum_in directo
    if total > 0 and (1.0001 < total <= 100.0001):
        pct = sum_in
    else:
        pct = (sum_in/total*100.0) if total > 0 else 0.0

    # ordenar listas solo por estética
    dentro.sort(); fuera.sort()
    return pct, dentro, fuera

# ========= CARGA =========
nect = pd.read_excel(F_NECT)
tol  = pd.read_excel(F_TOL)
dis  = pd.read_excel(F_DIS)
cru  = pd.read_excel(F_CRU)

for df in (nect, tol, dis, cru):
    df.columns = [norm(c) for c in df.columns]

# ========= DISMINUCIÓN (solo 500/600) =========
nect_adj = nect.copy()
cols_500_600 = [c for c in nect_adj.columns if str(c).startswith("500.0__") or str(c).startswith("600.0__")]
for c in cols_500_600:
    nect_adj[c] = pd.to_numeric(nect_adj[c], errors='coerce')

dis["VARIABLES"] = dis["VARIABLES"].astype(str).str.strip()
pct_col = "% DISMINUCION" if "% DISMINUCION" in dis.columns else dis.columns[1]
dis["frac"] = dis[pct_col].map(pct_to_fraction)
dis_map = dict(zip(dis["VARIABLES"], dis["frac"]))
for var, frac in dis_map.items():
    if var in nect_adj.columns:
        nect_adj[var] = nect_adj[var] * (1.0 - frac)

# ========= CALIBRES =========
# fuerza numérico también en 100.x por si vienen como texto
cal_map = parse_calibre_cols(nect_adj.columns)
for col in cal_map.keys():
    nect_adj[col] = pd.to_numeric(nect_adj[col], errors='coerce')

# ========= CRUCE 500/600 =========
cru_eff = cru.dropna(subset=["VARIABLES TOLERANCIAS","VARIABLE DE COMPARACION"]).copy()
cru_eff["VARIABLES TOLERANCIAS"] = cru_eff["VARIABLES TOLERANCIAS"].astype(str).str.strip()
cru_eff["VARIABLE DE COMPARACION"] = cru_eff["VARIABLE DE COMPARACION"].astype(str).str.strip()

mapped_defects = cru_eff[cru_eff["VARIABLE DE COMPARACION"].str.contains(r"^\d{3}\.0__", regex=True, na=False)]
defect_map = [
    (t, n, cat)
    for t, n, cat in mapped_defects[["VARIABLES TOLERANCIAS","VARIABLE DE COMPARACION","CATEGORIA"]].itertuples(index=False, name=None)
    if (n in nect_adj.columns) and (t in tol.columns)
]
cond_cols = [n for (_, n, cat) in defect_map if str(cat).upper() == "CONDICION"]
cali_cols = [n for (_, n, cat) in defect_map if str(cat).upper() == "CALIDAD"]

# ========= JOIN =========
join_keys = ["ESPECIE", "LINEA PRODUCTO"]
cand = nect_adj.merge(tol, on=join_keys, how="inner", suffixes=("", "_TOL"))

# ========= EVALUACIÓN =========
rows = []
for _, r in cand.iterrows():
    reasons = []
    ok_base = True  # reglas que bloquean (no incluye calibre)

    # BRIX
    tol_brix = r.get("BRIX", np.nan)
    brix_val = r.get("PROMSOLSOL", np.nan)
    if pd.notna(tol_brix) and tol_brix > 0:
        if pd.isna(brix_val) or brix_val < tol_brix:
            ok_base = False; reasons.append(f"BRIX {brix_val} < {tol_brix}")

    # FIRMEZA
    low  = r.get("FIRMEZA INFERIOR", np.nan)
    high = r.get("FIRMEZAS SUPERIORES", np.nan)
    firm = r.get("PROMFIRMEZA", np.nan)
    if (pd.notna(low) and low>0) or (pd.notna(high) and high>0):
        if pd.isna(firm):
            ok_base = False; reasons.append("Firmeza sin dato")
        else:
            if pd.notna(low) and low>0 and firm < low:
                ok_base = False; reasons.append(f"Firmeza {firm} < {low}")
            if pd.notna(high) and high>0 and firm > high:
                ok_base = False; reasons.append(f"Firmeza {firm} > {high}")

    # COLOR
    cmin = r.get("PORC_COLOR CUBRIMIENTO MIN", np.nan)
    color_ok_pct = np.nan
    if pd.notna(cmin) and cmin > 0:
        color_ok_pct = pct_color_ge(r, float(cmin))
        if color_ok_pct < float(cmin):
            ok_base = False; reasons.append(f"Color {color_ok_pct:.1f}% < {cmin}%")

    # Defectos individuales (máximos)
    for tol_name, nect_name, _cat in defect_map:
        tol_val = r.get(tol_name, np.nan)
        x_val   = r.get(nect_name, np.nan)
        if pd.notna(tol_val) and pd.notna(x_val) and x_val > tol_val:
            ok_base = False; reasons.append(f"{tol_name}: {x_val} > {tol_val}")

    # Sumatorias
    sum_cond = float(sum((r.get(c, 0.0) if pd.notna(r.get(c, np.nan)) else 0.0) for c in cond_cols))
    sum_cali = float(sum((r.get(c, 0.0) if pd.notna(r.get(c, np.nan)) else 0.0) for c in cali_cols))
    lim_cond = r.get("SUMATORIA CONDICION", np.nan)
    lim_cali = r.get("SUMATORIA CALIDAD", np.nan)
    if pd.notna(lim_cond) and lim_cond>0 and sum_cond > lim_cond:
        ok_base = False; reasons.append(f"Sum CONDICION {sum_cond} > {lim_cond}")
    if pd.notna(lim_cali) and lim_cali>0 and sum_cali > lim_cali:
        ok_base = False; reasons.append(f"Sum CALIDAD {sum_cali} > {lim_cali}")

    # Calibres: % en rango + listas (NO bloquea)
    cal_inf = r.get("CALIBRE INFERIOR", np.nan)
    cal_sup = r.get("CALIBRE SUPERIOR", np.nan)
    pct_cal_in, dentro, fuera = pct_calibres_en_rango_y_listas(r, cal_map, cal_inf, cal_sup)

    kilos = r.get("KILOS_REAL", 0.0) or 0.0
    asignable = kilos * (pct_cal_in/100.0) if ok_base else 0.0

    calidad_vals   = {f"CAL_{c}": (r.get(c, np.nan)) for c in cali_cols}
    condicion_vals = {f"CON_{c}": (r.get(c, np.nan)) for c in cond_cols}

    rows.append({
        "LOTE": r.get("LOTE"),
        "MERCADO-CLIENTE": r.get("MERCADO-CLIENTE"),
        "ESPECIE": r.get("ESPECIE"),
        "LINEA PRODUCTO": r.get("LINEA PRODUCTO"),
        "KILOS_REAL": kilos,
        "ASIGNABLE_KG": asignable,
        "PASA_BASE": ok_base,
        "RAZONES": "; ".join(reasons),
        "SUM_CALIDAD": sum_cali,
        "LIM_CALIDAD": lim_cali,
        "SUM_CONDICION": sum_cond,
        "LIM_CONDICION": lim_cond,
        "%CALIBRES_EN_RANGO": pct_cal_in,
        "CALIBRES_DENTRO": ", ".join(map(str, dentro)),
        "CALIBRES_FUERA": ", ".join(map(str, fuera)),
        "BRIX_VAL": brix_val,
        "FIRMEZA_VAL": firm,
        "COLOR_OK_%": color_ok_pct,
        **calidad_vals,
        **condicion_vals
    })

detalle = pd.DataFrame(rows)

# ========= RESÚMENES =========
res_mc = (detalle
          .groupby("MERCADO-CLIENTE", as_index=False)
          .agg(LOTES_OK=("PASA_BASE","sum"),
               KILOS_ASIGNABLE=("ASIGNABLE_KG","sum"))
          .sort_values("KILOS_ASIGNABLE", ascending=False))

res_lote = (detalle
            .groupby("LOTE", as_index=False)
            .agg(KILOS=("KILOS_REAL","first"),
                 MEJORES_MERCADOS=("ASIGNABLE_KG", lambda s: int((s>0).sum())),
                 TOTAL_ASIGNABLE=("ASIGNABLE_KG","sum"))
            .sort_values("TOTAL_ASIGNABLE", ascending=False))

# ========= (OPCIONAL) CHECK LOTE =========
def build_check_sheet_for_lote(lote_id: int) -> pd.DataFrame:
    mask_real = nect["LOTE"] == lote_id
    mask_adj  = nect_adj["LOTE"] == lote_id
    if not mask_real.any() or not mask_adj.any():
        return pd.DataFrame(columns=["Variable","Valor Real","%Disminucion","Valor Disminuido"])
    row_real = nect.loc[mask_real].iloc[0]
    row_adj  = nect_adj.loc[mask_adj].iloc[0]
    vars_list = [v for v in dis["VARIABLES"].unique() if v in cols_500_600]
    rows_ck = []
    for v in vars_list:
        real = pd.to_numeric(row_real.get(v, np.nan), errors="coerce")
        adj  = pd.to_numeric(row_adj.get(v, np.nan), errors="coerce")
        frac = dis_map.get(v, 0.0)
        rows_ck.append([v, real, f"{frac*100:.2f}%", adj])
    return pd.DataFrame(rows_ck, columns=["Variable","Valor Real","%Disminucion","Valor Disminuido"])

# ========= ESCRITURA =========
# Seleccionar motor disponible
try:
    import xlsxwriter  # noqa
    writer_engine = "xlsxwriter"
except ImportError:
    writer_engine = "openpyxl"  # requiere 'pip install openpyxl'

with pd.ExcelWriter(OUT_XLSX, engine=writer_engine) as xw:
    detalle.to_excel(xw, index=False, sheet_name="AsignacionDetalle")
    res_mc.to_excel(xw, index=False, sheet_name="ResumenMC")
    res_lote.to_excel(xw, index=False, sheet_name="ResumenLote")
    if CHECK_LOTE is not None:
        build_check_sheet_for_lote(CHECK_LOTE).to_excel(
            xw, index=False, sheet_name=f"Check_{CHECK_LOTE}"
        )

print(f"Archivo generado: {OUT_XLSX.resolve()}")
