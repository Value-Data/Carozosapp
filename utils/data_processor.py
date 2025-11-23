"""Procesamiento de lotes y asignación a mercado-cliente"""

import numpy as np
import pandas as pd

from .helpers import (
    norm_cols,
    normalize_bounds,
    parse_calibre_cols,
    pct_to_fraction,
    pick_col,
)


def pct_color_ge(row: pd.Series, threshold: float) -> float:
    """Calcula porcentaje de color >= threshold."""
    color_bins = ["400.0__0 - 30", "400.0__30-50", "400.0__50-75", "400.0__75-100"]
    bin_lower = {"400.0__0 - 30": 0, "400.0__30-50": 30, "400.0__50-75": 50, "400.0__75-100": 75}
    acc, total = 0.0, 0.0
    for b in color_bins:
        val = row.get(b, 0.0)
        if pd.isna(val):
            val = 0.0
        total += val
        if bin_lower[b] >= threshold:
            acc += val
    if total > 0 and (1.0001 < total <= 100.0001):
        return acc  # ya está en %
    return (acc / total * 100.0) if total > 0 else 0.0


def pct_calibres_en_rango_y_listas(row, cal_map, cal_inf, cal_sup):
    """Calcula % en rango y lista de calibres dentro/fuera, normalizando rangos invertidos."""
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
            if val > 0:
                dentro.append(cal)
        elif val > 0:
            fuera.append(cal)

    if total > 0 and (1.0001 < total <= 100.0001):
        pct = sum_in
    else:
        pct = (sum_in / total * 100.0) if total > 0 else 0.0

    dentro.sort()
    fuera.sort()
    return pct, dentro, fuera


def process_asignacion(
    lotes_df,
    tolerancias_df,
    disminucion_df,
    cruce_df,
    especie=None,
    linea_producto=None,
):
    """Procesa asignación de lotes a mercado-cliente.

    Args:
        lotes_df: DataFrame con datos de lotes
        tolerancias_df: DataFrame con tolerancias por mercado-cliente
        disminucion_df: DataFrame con porcentajes de disminución
        cruce_df: DataFrame con cruce de variables
        especie: Nombre de especie (para filtrar)
        linea_producto: Línea de producto (para filtrar)

    Returns:
        dict con:
            - 'detalle': DataFrame detallado por lote y mercado-cliente
            - 'resumen_mc': Resumen por mercado-cliente
            - 'resumen_lote': Resumen por lote

    """
    # Normalizar columnas
    for df in [lotes_df, tolerancias_df, disminucion_df, cruce_df]:
        norm_cols(df)

    # NO filtrar aquí - el join por ESPECIE y LINEA PRODUCTO ya hace el filtrado

    # Aplicar disminuciones (solo 500/600)
    lotes_adj = lotes_df.copy()
    cols_500_600 = [
        c for c in lotes_adj.columns if str(c).startswith("500.0__") or str(c).startswith("600.0__")
    ]
    for c in cols_500_600:
        lotes_adj[c] = pd.to_numeric(lotes_adj[c], errors="coerce")

    disminucion_df["VARIABLES"] = disminucion_df["VARIABLES"].astype(str).str.strip()
    pct_col = (
        "% DISMINUCION" if "% DISMINUCION" in disminucion_df.columns else disminucion_df.columns[1]
    )
    disminucion_df["frac"] = disminucion_df[pct_col].map(pct_to_fraction)
    dis_map = dict(zip(disminucion_df["VARIABLES"], disminucion_df["frac"]))
    for var, frac in dis_map.items():
        if var in lotes_adj.columns:
            lotes_adj[var] = lotes_adj[var] * (1.0 - frac)

    # Calibres
    cal_map = parse_calibre_cols(lotes_adj.columns)
    for col in cal_map.keys():
        lotes_adj[col] = pd.to_numeric(lotes_adj[col], errors="coerce")

    # Cruce 500/600
    cru_eff = cruce_df.dropna(subset=["VARIABLES TOLERANCIAS", "VARIABLE DE COMPARACION"]).copy()
    cru_eff["VARIABLES TOLERANCIAS"] = cru_eff["VARIABLES TOLERANCIAS"].astype(str).str.strip()
    cru_eff["VARIABLE DE COMPARACION"] = cru_eff["VARIABLE DE COMPARACION"].astype(str).str.strip()

    mapped_defects = cru_eff[
        cru_eff["VARIABLE DE COMPARACION"].str.contains(r"^\d{3}\.0__", regex=True, na=False)
    ]
    defect_map = [
        (t, n, cat)
        for t, n, cat in mapped_defects[
            ["VARIABLES TOLERANCIAS", "VARIABLE DE COMPARACION", "CATEGORIA"]
        ].itertuples(index=False, name=None)
        if (n in lotes_adj.columns) and (t in tolerancias_df.columns)
    ]
    cond_cols = [n for (_, n, cat) in defect_map if str(cat).upper() == "CONDICION"]
    cali_cols = [n for (_, n, cat) in defect_map if str(cat).upper() == "CALIDAD"]

    # Join
    join_keys = ["ESPECIE", "LINEA PRODUCTO"]

    # Verificar que las columnas existan
    for key in join_keys:
        if key not in lotes_adj.columns:
            raise ValueError(
                f"Columna '{key}' no encontrada en lotes. Columnas disponibles: {list(lotes_adj.columns)}",
            )
        if key not in tolerancias_df.columns:
            raise ValueError(
                f"Columna '{key}' no encontrada en tolerancias. Columnas disponibles: {list(tolerancias_df.columns)}",
            )

    cand = lotes_adj.merge(tolerancias_df, on=join_keys, how="inner", suffixes=("", "_TOL"))

    if len(cand) == 0:
        raise ValueError(
            f"No se encontraron coincidencias entre lotes y tolerancias para la combinación especificada. "
            f"Lotes: {len(lotes_adj)} filas, Tolerancias: {len(tolerancias_df)} filas",
        )

    # Evaluación
    rows = []
    for _, r in cand.iterrows():
        reasons = []
        ok_base = True

        # BRIX
        tol_brix = r.get("BRIX", np.nan)
        brix_val = r.get("PROMSOLSOL", np.nan)
        if pd.notna(tol_brix) and tol_brix > 0:
            if pd.isna(brix_val) or brix_val < tol_brix:
                ok_base = False
                reasons.append(f"BRIX {brix_val} < {tol_brix}")

        # FIRMEZA
        low = r.get("FIRMEZA INFERIOR", np.nan)
        high = r.get("FIRMEZAS SUPERIORES", np.nan)
        firm = r.get("PROMFIRMEZA", np.nan)
        if (pd.notna(low) and low > 0) or (pd.notna(high) and high > 0):
            if pd.isna(firm):
                ok_base = False
                reasons.append("Firmeza sin dato")
            else:
                if pd.notna(low) and low > 0 and firm < low:
                    ok_base = False
                    reasons.append(f"Firmeza {firm} < {low}")
                if pd.notna(high) and high > 0 and firm > high:
                    ok_base = False
                    reasons.append(f"Firmeza {firm} > {high}")

        # COLOR
        cmin = r.get("PORC_COLOR CUBRIMIENTO MIN", np.nan)
        color_ok_pct = np.nan
        if pd.notna(cmin) and cmin > 0:
            color_ok_pct = pct_color_ge(r, float(cmin))
            if color_ok_pct < float(cmin):
                ok_base = False
                reasons.append(f"Color {color_ok_pct:.1f}% < {cmin}%")

        # Defectos individuales
        for tol_name, nect_name, _cat in defect_map:
            tol_val = r.get(tol_name, np.nan)
            x_val = r.get(nect_name, np.nan)
            if pd.notna(tol_val) and pd.notna(x_val) and x_val > tol_val:
                ok_base = False
                reasons.append(f"{tol_name}: {x_val} > {tol_val}")

        # Sumatorias
        sum_cond = float(
            sum((r.get(c, 0.0) if pd.notna(r.get(c, np.nan)) else 0.0) for c in cond_cols),
        )
        sum_cali = float(
            sum((r.get(c, 0.0) if pd.notna(r.get(c, np.nan)) else 0.0) for c in cali_cols),
        )
        lim_cond = r.get("SUMATORIA CONDICION", np.nan)
        lim_cali = r.get("SUMATORIA CALIDAD", np.nan)
        if pd.notna(lim_cond) and lim_cond > 0 and sum_cond > lim_cond:
            ok_base = False
            reasons.append(f"Sum CONDICION {sum_cond} > {lim_cond}")
        if pd.notna(lim_cali) and lim_cali > 0 and sum_cali > lim_cali:
            ok_base = False
            reasons.append(f"Sum CALIDAD {sum_cali} > {lim_cali}")

        # Calibres
        cal_inf = r.get("CALIBRE INFERIOR", np.nan)
        cal_sup = r.get("CALIBRE SUPERIOR", np.nan)
        pct_cal_in, dentro, fuera = pct_calibres_en_rango_y_listas(r, cal_map, cal_inf, cal_sup)

        kilos = r.get("KILOS_REAL", 0.0) or 0.0
        asignable = kilos * (pct_cal_in / 100.0) if ok_base else 0.0

        calidad_vals = {f"CAL_{c}": (r.get(c, np.nan)) for c in cali_cols}
        condicion_vals = {f"CON_{c}": (r.get(c, np.nan)) for c in cond_cols}

        rows.append(
            {
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
                **condicion_vals,
            },
        )

    detalle = pd.DataFrame(rows)

    if len(detalle) == 0:
        raise ValueError(
            "No se generaron filas en el procesamiento. Verifique que haya coincidencias entre lotes y tolerancias.",
        )

    # Resúmenes
    # Verificar que existe la columna MERCADO-CLIENTE
    if "MERCADO-CLIENTE" not in detalle.columns and "MERCADO_CLIENTE" not in detalle.columns:
        # Intentar encontrar la columna con pick_col
        try:
            col_mc_detalle = pick_col(
                detalle,
                ["MERCADO-CLIENTE", "MERCADO_CLIENTE", "MERCADOCLIENTE"],
            )
        except KeyError:
            raise ValueError(
                f"Columna MERCADO-CLIENTE no encontrada. Columnas disponibles: {list(detalle.columns)}",
            )
    else:
        col_mc_detalle = (
            "MERCADO-CLIENTE" if "MERCADO-CLIENTE" in detalle.columns else "MERCADO_CLIENTE"
        )

    res_mc = (
        detalle.groupby(col_mc_detalle, as_index=False)
        .agg(LOTES_OK=("PASA_BASE", "sum"), KILOS_ASIGNABLE=("ASIGNABLE_KG", "sum"))
        .sort_values("KILOS_ASIGNABLE", ascending=False)
    )

    # Renombrar para consistencia
    if col_mc_detalle != "MERCADO-CLIENTE":
        res_mc.rename(columns={col_mc_detalle: "MERCADO-CLIENTE"}, inplace=True)

    res_lote = (
        detalle.groupby("LOTE", as_index=False)
        .agg(
            KILOS=("KILOS_REAL", "first"),
            MEJORES_MERCADOS=("ASIGNABLE_KG", lambda s: int((s > 0).sum())),
            TOTAL_ASIGNABLE=("ASIGNABLE_KG", "sum"),
        )
        .sort_values("TOTAL_ASIGNABLE", ascending=False)
    )

    return {"detalle": detalle, "resumen_mc": res_mc, "resumen_lote": res_lote}
