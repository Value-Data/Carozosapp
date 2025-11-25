# -*- coding: utf-8 -*-
"""Funciones auxiliares comunes"""

import pandas as pd
import numpy as np
import unicodedata
import re


def norm(s):
    """Normaliza string: strip."""
    return str(s).strip()


def norm_cols(df):
    """Normaliza nombres de columnas."""
    df.columns = [str(c).strip() for c in df.columns]
    return df


def canon(s: str) -> str:
    """
    Canonicaliza string para comparación.
    Normaliza unicode, quita acentos, espacios, guiones, etc.
    """
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper().strip()
    return s.replace(" ", "").replace("_", "").replace("-", "").replace("/", "")


def pick_col(df, candidates):
    """
    Busca una columna en el dataframe usando nombres canónicos.
    Intenta coincidencias exactas primero, luego parciales.
    """
    cmap = {canon(c): c for c in df.columns}
    # Primero intenta coincidencias exactas
    for cand in candidates:
        if canon(cand) in cmap:
            return cmap[canon(cand)]
    # Luego intenta coincidencias parciales
    for c in df.columns:
        if any(canon(cand) in canon(c) for cand in candidates):
            return c
    raise KeyError(f"No se encontró ninguna de {candidates}. Columnas disponibles: {list(df.columns)}")


def pct_to_fraction(x) -> float:
    """
    Convierte porcentaje a fracción.
    '96,6%' -> 0.966 ; '96.6' -> 0.966 ; 0.966 -> 0.966
    """
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace('%', '').replace(',', '.')
    try:
        v = float(s)
    except Exception:
        v = pd.to_numeric(x, errors='coerce')
        if pd.isna(v):
            return 0.0
    return v/100.0 if v > 1.0 else v


def to_num_series(ser: pd.Series) -> pd.Series:
    """Convierte serie a numérica, limpiando formato."""
    return (ser.astype(str)
            .str.replace("%", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.replace("\xa0", "", regex=False)
            .str.replace(r"[^0-9\.\-]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce"))


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
    return (lo, hi)


def parse_calibre_cols(cols):
    """Devuelve dict {col_name: int_calibre} para columnas 100.0__XX"""
    cal_map = {}
    for c in cols:
        if str(c).startswith("100.0__"):
            m = re.search(r"100\.0__([0-9]+)", str(c))
            if m:
                cal_map[c] = int(m.group(1))
    return cal_map




