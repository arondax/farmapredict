# Guardado genérico de modelos pydantic en la capa raw

import json
import os
import re
import unicodedata
import glob

from collections.abc import Sequence
from datetime import datetime

from pandas import DataFrame
from pydantic import BaseModel

from src.config import *

#Funciones de utilidad

def _slug(texto: str) -> str:
    """
    Convierte un texto en un slug, es decir, una versión simplificada y legible del texto,
    eliminando acentos, caracteres especiales y espacios.

    Args:
        texto (str): El texto a convertir en slug.
    """
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()

def _timestamp() -> str:
    # TODO (ya anotado): pasar a UTC. Hoy es hora local, igual que guardar_modelos,
    # para que limpieza_medicamentos (ZONA_SNAPSHOT) lo siga interpretando bien.
    return datetime.now().strftime("%Y%m%d_%H%M%S")

#Funciones principales de la API

def snapshot_del_dia(nombre: str, subcarpeta: str = "cima", fecha: datetime | None = None) -> str | None:
    """Devuelve la ruta del snapshot de `nombre` del día indicado (hoy por defecto), o None."""
    fecha = fecha or datetime.now()
    patron = os.path.join(DATA_RAW_DIR, subcarpeta, f"{_slug(nombre)}_{fecha:%Y%m%d}_*.json")
    existentes = sorted(glob.glob(patron))
    return existentes[-1] if existentes else None

def guardar_modelos(modelos: BaseModel | Sequence[BaseModel], nombre: str, subcarpeta: str = "cima") -> str:
    """
    Guarda la información de un medicamento en un archivo JSON.

    Args:
        medicamento (schemas.Medicamento): El objeto Medicamento a guardar.
        nombre (str): Nombre del medicamento para generar el nombre del archivo.

    Returns:
    """
    if isinstance (modelos, BaseModel):
        modelos = [modelos]
    
    carpeta = os.path.join(DATA_RAW_DIR, subcarpeta)
    os.makedirs(carpeta, exist_ok=True)

    timestamp = _timestamp()
    ruta = os.path.join(carpeta, f"{_slug(nombre)}_{timestamp}.json")

    datos = [m.model_dump(mode="json") for m in modelos]

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    return ruta

def guardar_csv(
    df: DataFrame,
    nombre: str,
    carpeta: str = DATA_PROCESSED_DIR,
    timestamp: str | None = None,
    sep: str = ";",
    encoding: str = "utf-8",
) -> str:
    """
    Guarda un DataFrame como CSV dentro de una carpeta de data/.

    Args:
        df: DataFrame a guardar.
        nombre: Nombre base del archivo (se pasa por _slug).
        carpeta: Carpeta destino (DATA_PROCESSED_DIR, DATA_CLEANED_DIR...).
        timestamp: Sufijo opcional "YYYYmmdd_HHMMSS", igual que en guardar_modelos.
        sep: Separador del CSV.
        encoding: Codificación del archivo.

    Returns:
        Ruta absoluta del archivo guardado.
    """
    os.makedirs(carpeta, exist_ok=True)

    nombre_archivo = _slug(nombre)
    if timestamp:
        nombre_archivo = f"{nombre_archivo}_{timestamp}"

    ruta = os.path.join(carpeta, f"{nombre_archivo}.csv")
    df.to_csv(ruta, sep=sep, encoding=encoding, index=False)
    return ruta

def guardar_raw(registros: list[dict], nombre: str, subcarpeta: str = "cima") -> str:
    """
    Guarda la respuesta de la API tal cual (sin pasar por Pydantic) en data/raw.
    Escritura atómica: se escribe en .tmp y se renombra al final, para que un
    fallo a mitad no deje un JSON corrupto con el nombre definitivo.
    """
    carpeta = os.path.join(DATA_RAW_DIR, subcarpeta)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{_slug(nombre)}_{_timestamp()}.json")

    tmp = f"{ruta}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False)
    os.replace(tmp, ruta)
    return ruta