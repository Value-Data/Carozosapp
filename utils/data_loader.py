# -*- coding: utf-8 -*-
"""Carga y gestión de datos por especie"""

from pathlib import Path
import pandas as pd
from .helpers import norm, norm_cols


# Configuración de especies disponibles
ESPECIES_CONFIG = {
    "Ciruela Negra": {
        "lotes": "Data/Lotes_CiruelaNeg.xlsx",
        "tolerancias": "Data/Tolerancia_CiruelaNeg.xlsx"
    },
    "Ciruela Candy": {
        "lotes": "Data/Lotes_CiruelarCan.xlsx",
        "tolerancias": "Data/Tolerancia_CiruelaCan.xlsx"
    },
    "Ciruela Roja": {
        "lotes": "Data/Lotes_CiruelarRoj.xlsx",
        "tolerancias": "Data/Tolerancia_CiruelaRoj.xlsx"
    },
    "Durazno Amarillo": {
        "lotes": "Data/Lotes_DuraznoAm.xlsx",
        "tolerancias": "Data/Tolerancia_DuraznoAm.xlsx"
    },
    "Durazno Blanco": {
        "lotes": "Data/Lotes_DuraznoBl.xlsx",
        "tolerancias": "Data/Tolerancia_DuraznoBl.xlsx"
    },
    "Nectarin Amarillo": {
        "lotes": "Data/Lotes_NectarinAm.xlsx",
        "tolerancias": "Data/Tolerancia_NectarinAm.xlsx"
    },
    "Nectarin Blanco": {
        "lotes": "Data/Lotes_NectarinBl.xlsx",
        "tolerancias": "Data/Tolerancia_NectarinBl.xlsx"
    }
}

# Archivos compartidos
F_DISMINUCION = "Disminucion.xlsx"
F_CRUCE = "Cruce de Variables.xlsx"


def get_especies_disponibles():
    """Retorna lista de especies disponibles."""
    return list(ESPECIES_CONFIG.keys())


def get_lineas_producto(especie: str, base_dir: Path = None) -> list:
    """
    Lee los archivos de lotes y extrae las líneas de producto disponibles.
    
    Args:
        especie: Nombre de la especie
        base_dir: Directorio base (default: Path("."))
    
    Returns:
        Lista de líneas de producto únicas
    """
    if base_dir is None:
        base_dir = Path(".")
    
    if especie not in ESPECIES_CONFIG:
        raise ValueError(f"Especie '{especie}' no encontrada. Disponibles: {get_especies_disponibles()}")
    
    archivo_lotes = base_dir / ESPECIES_CONFIG[especie]["lotes"]
    
    if not archivo_lotes.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {archivo_lotes}")
    
    try:
        df_lotes = pd.read_excel(archivo_lotes)
        norm_cols(df_lotes)
        
        if "LINEA PRODUCTO" not in df_lotes.columns:
            # Intentar con nombre canónico
            from .helpers import pick_col
            col_linea = pick_col(df_lotes, ["LINEA PRODUCTO", "LINEA_PRODUCTO", "LINEAPRODUCTO"])
            return sorted(df_lotes[col_linea].dropna().unique().tolist())
        
        return sorted(df_lotes["LINEA PRODUCTO"].dropna().unique().tolist())
    except Exception as e:
        raise RuntimeError(f"Error al leer archivo {archivo_lotes}: {str(e)}")


def load_data(especie: str, linea_producto: str = None, base_dir: Path = None):
    """
    Carga datos de lotes y tolerancias para una especie.
    
    Args:
        especie: Nombre de la especie
        linea_producto: Línea de producto (opcional, para filtrar)
        base_dir: Directorio base (default: Path("."))
    
    Returns:
        dict con:
            - 'lotes': DataFrame de lotes
            - 'tolerancias': DataFrame de tolerancias
            - 'disminucion': DataFrame de disminuciones
            - 'cruce': DataFrame de cruce de variables
    """
    if base_dir is None:
        base_dir = Path(".")
    
    if especie not in ESPECIES_CONFIG:
        raise ValueError(f"Especie '{especie}' no encontrada")
    
    # Cargar archivos de especie
    archivo_lotes = base_dir / ESPECIES_CONFIG[especie]["lotes"]
    archivo_tolerancias = base_dir / ESPECIES_CONFIG[especie]["tolerancias"]
    
    # Cargar archivos compartidos
    archivo_disminucion = base_dir / F_DISMINUCION
    archivo_cruce = base_dir / F_CRUCE
    
    # Verificar existencia
    for archivo in [archivo_lotes, archivo_tolerancias, archivo_disminucion, archivo_cruce]:
        if not archivo.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {archivo}")
    
    # Cargar datos
    lotes = pd.read_excel(archivo_lotes)
    tolerancias = pd.read_excel(archivo_tolerancias)
    disminucion = pd.read_excel(archivo_disminucion)
    cruce = pd.read_excel(archivo_cruce)
    
    # Normalizar columnas
    for df in [lotes, tolerancias, disminucion, cruce]:
        norm_cols(df)
    
    # Filtrar por línea de producto si se especifica
    if linea_producto:
        if "LINEA PRODUCTO" in lotes.columns:
            lotes = lotes[lotes["LINEA PRODUCTO"] == linea_producto].copy()
        if "LINEA PRODUCTO" in tolerancias.columns:
            tolerancias = tolerancias[tolerancias["LINEA PRODUCTO"] == linea_producto].copy()
    
    return {
        'lotes': lotes,
        'tolerancias': tolerancias,
        'disminucion': disminucion,
        'cruce': cruce
    }




