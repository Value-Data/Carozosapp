"""Función unificada para procesamiento completo"""

from pathlib import Path

from .cluster_processor import process_clusters
from .data_loader import load_data
from .data_processor import process_asignacion


def process_species_linea(
    especie: str,
    linea_producto: str,
    k=5,
    qmin=None,
    qmax=None,
    base_dir: Path = None,
):
    """Procesa una combinación ESPECIE + LÍNEA PRODUCTO y genera todos los resultados.

    Args:
        especie: Nombre de la especie
        linea_producto: Línea de producto
        k: Número de clusters (default: 5)
        qmin: Lista de cuantiles MIN (default: [0.9, 0.7, 0.5, 0.3, 0.1])
        qmax: Lista de cuantiles MAX (default: [0.1, 0.3, 0.5, 0.7, 0.9])
        base_dir: Directorio base (default: Path("."))

    Returns:
        dict con todos los resultados:
            - 'asignacion': resultados de asignación (detalle, resumen_mc, resumen_lote)
            - 'clusters': resultados de clusters (todos los DataFrames de tolerancias)

    """
    if base_dir is None:
        base_dir = Path()

    # Cargar datos
    datos = load_data(especie, linea_producto, base_dir)

    # Procesar asignación
    asignacion = process_asignacion(
        datos["lotes"],
        datos["tolerancias"],
        datos["disminucion"],
        datos["cruce"],
        especie=especie,
        linea_producto=linea_producto,
    )

    # Procesar clusters
    clusters = process_clusters(
        asignacion["resumen_mc"],
        datos["tolerancias"],
        datos["cruce"],
        k=k,
        qmin=qmin,
        qmax=qmax,
    )

    return {
        "asignacion": asignacion,
        "clusters": clusters,
        "especie": especie,
        "linea_producto": linea_producto,
    }
