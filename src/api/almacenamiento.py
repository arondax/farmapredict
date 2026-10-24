# Guardado genérico de modelos pydantic en la capa raw

import json
import os
import re
import unicodedata
from collections.abc import Sequence
from datetime import datetime

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

#Funciones principales de la API

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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"{_slug(nombre)}_{timestamp}.json")

    datos = [m.model_dump(mode="json") for m in modelos]

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    return ruta

def guardar_csv(df: DataFrame, nombre: str, sep: str = ";", encoding: str = "utf-8")-> None:
    carpeta = os.path.join(DATA_PROCESSED_DIR)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"{_slug(nombre)}.csv")
    df.to_csv(ruta, sep=sep, encoding=encoding, index=False)