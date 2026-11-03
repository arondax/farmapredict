from datetime import datetime
import os
import pandas as pd

from src.api.almacenamiento import guardar_csv
from src.config import *

# TODO (pendiente tras la revisión del 03/11/2026):
#
# Datos / recomendador
# - Añadir "dosis_norm" a COLUMNAS_NORM: mayúsculas y sin espacios junto a "/"
#   (1.073 dosis tipo "600 mg/ 300 mg" vs "600 mg/300 mg" en el snapshot 20261019).
# - Si la dosis contiene "REVISAR" (marcador interno de CIMA, 35 casos), dejar
#   dosis_norm a nulo y contarlos en el print de limpiar_medicamentos.
# - Fechas de CIMA: son medianoche hora de Madrid guardadas en UTC (el 57 % cae
#   en el día anterior). Convertir con .dt.tz_convert("Europe/Madrid") donde se
#   muestren (dashboard/API); para features no afecta.
#
# Repo / PR
# - .gitignore: excluir data/** (con !data/**/.gitkeep), __pycache__/ y *.pyc.
# - README: cómo ejecutar (python -m src.main) y qué va en raw/processed/cleaned.
# - Test PyTest de limpiar_medicamentos: duplicado, nregistro nulo y booleano en texto.
#
# Otros módulos
# - transformaciones.py: quitar el print por medicamento y corregir
#   med.get("formaFarmaceuticaSimplificada" or {}) -> (med.get(...) or {}).get("nombre").
# - almacenamiento.guardar_modelos: generar el timestamp en UTC (ahora usa la hora
#   local, por eso ZONA_SNAPSHOT = "Europe/Madrid").





#Columnas que se van a extraer del dataset original
MAPA_COLUMNAS = {
    "nregistro": "nregistro",
    "nombre": "nombre_medicamento",
    "vtm": "principio_activo",
    "dosis": "dosis",
    "forma_farmaceutica": "forma_farmaceutica",
    "vias": "via_administracion",
    "labtitular": "laboratorio",
    "cpresc": "condiciones_prescripcion",
    "comerc": "es_comercializado",
    "receta": "requiere_receta",
    "generico": "es_generico",
    "psum": "problema_suministro",
    "fecha_aut": "fecha_autorizacion",
    "fecha_rev": "fecha_revision",
}

COLUMNAS_FECHA = ["fecha_autorizacion", "fecha_revision"]

COLUMNAS_BOOL = [
    "es_comercializado",
    "requiere_receta",
    "es_generico",
    "problema_suministro",
]

COLUMNAS_TEXTO = [c for c in MAPA_COLUMNAS.values() if c not in COLUMNAS_FECHA + COLUMNAS_BOOL]

MAPA_BOOL = {"true": True, "false": False, "1": True, "0": False}

# columna origen -> columna normalizada para el recomendador
COLUMNAS_NORM = {
    "principio_activo": "principio_activo_norm",
    "forma_farmaceutica": "forma_farmaceutica_norm",
}
#Funciones auxiliares

def _normalizar_clave(serie: pd.Series) -> pd.Series:
    """
    Normaliza una serie de texto para crear una clave canónica.
    Convierte a mayúsculas, elimina acentos y caracteres especiales.

    Args:
        serie (pd.Series): Serie de texto a normalizar.
    Returns:
        pd.Series: Serie normalizada.
    """
    return (
    serie
    .str.normalize("NFD")
    .str.replace(r"[\u0300-\u036f]", "", regex=True)
    .str.upper()
    )
     
def _renombrar_y_ordenar(df) -> pd.DataFrame:
    """
    Renombra las columnas del DataFrame según el mapa de columnas y las ordena.

    Args:
        df (pd.DataFrame): DataFrame original.
    Returns:
        pd.DataFrame: DataFrame con columnas renombradas y ordenadas.
    """
    faltan = set(MAPA_COLUMNAS) - set(df.columns)
    if faltan:
      raise ValueError(f"Faltan columnas en la entrada: {sorted(faltan)}")
    return df.rename(columns=MAPA_COLUMNAS)[list(MAPA_COLUMNAS.values())]

def _limpiar_texto(df) -> pd.DataFrame:
    """
    Limpia los campos de texto del DataFrame eliminando saltos de línea, tabulaciones y espacios extra.

    Args:
        df (pd.DataFrame): DataFrame original.
    Returns:
        pd.DataFrame: DataFrame con campos de texto limpios.
    """
    df = df.copy()
    for col in COLUMNAS_TEXTO:
        df[col] = (
            df[col]
            .astype("string")
            .str.replace(r"[\r\n\t]", " ", regex=True)  # Elimina saltos de línea y tabulaciones
            .str.replace(r"\s+", " ", regex=True)  # Elimina espacios dobles
            .str.strip()  # Elimina espacios al inicio y final
        )
    return df

def _tipar_columnas(df) -> pd.DataFrame:
    """
    Tipifica las columnas del DataFrame según su tipo esperado.

    Args:
        df (pd.DataFrame): DataFrame original.
    Returns:
        pd.DataFrame: DataFrame con columnas tipadas.
    """
    # Tipar columnas de fecha
    df = df.copy()
    for col in COLUMNAS_FECHA:
        df[col] = pd.to_datetime(df[col], utc=True)
    for col in COLUMNAS_BOOL:
        df[col] = df[col].astype("string").str.lower().map(MAPA_BOOL).astype("boolean")
    return df

def _agregar_claves_norm(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas *_norm que usará el recomendador de sustitutivos."""
    df = df.copy()
    for origen, destino in COLUMNAS_NORM.items():
        df[destino] = _normalizar_clave(df[origen])
    return df

ZONA_SNAPSHOT = "Europe/Madrid"
CLAVE_SNAPSHOT = ["nregistro", "fecha_snapshot"]

#Funcion principal de limpieza de medicamentos
def limpiar_medicamentos(df: pd.DataFrame, fecha_snapshot: datetime) -> pd.DataFrame:
    """
    Limpia y tipa el catálogo de medicamentos de un snapshot de CIMA.

    No lee ni escribe archivos: recibe el DataFrame de transformaciones y
    devuelve el DataFrame limpio, listo para guardar o cargar en la BD.

    Args:
        df: DataFrame con las columnas originales de CIMA (salida de extraer_medicamentos).
        fecha_snapshot: Momento de descarga del snapshot (timestamp del JSON raw).
            Si no trae zona horaria, se interpreta como hora de Madrid.

    Returns:
        DataFrame limpio con la columna fecha_snapshot (UTC) y sin duplicados
        por (nregistro, fecha_snapshot).
    """
    df = _renombrar_y_ordenar(df)
    df = _limpiar_texto(df)
    df = _tipar_columnas(df)
    df = _agregar_claves_norm(df)

    ts = pd.Timestamp(fecha_snapshot)
    if ts.tzinfo is None:
        ts = ts.tz_localize(ZONA_SNAPSHOT)
    df["fecha_snapshot"] = ts.tz_convert("UTC")

    # Validaciones: clave obligatoria y duplicados (Fase 1, 8.1)
    n_inicial = len(df)
    df = df.dropna(subset=["nregistro"])
    sin_clave = n_inicial - len(df)

    df = df.drop_duplicates(subset=CLAVE_SNAPSHOT)
    duplicados = n_inicial - sin_clave - len(df)

    print(
        f"Limpieza: {n_inicial} filas de entrada | {sin_clave} sin nregistro | "
        f"{duplicados} duplicadas | {len(df)} finales"
    )
    return df.reset_index(drop=True)

