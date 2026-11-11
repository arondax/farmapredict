import glob
import json
import os
import re
import time
from datetime import datetime

import pandas as pd

from src.config import DATA_PROCESSED_DIR, DATA_RAW_DIR, DATA_CLEANED_DIR
from src.api.api import get_medicamentos_pagina, get_todos_medicamentos
from src.api.almacenamiento import guardar_csv, guardar_modelos
from src.api.transformaciones import extraer_medicamentos
from src.api.limpieza_medicamentos import limpiar_medicamentos, MAPA_COLUMNAS

PATRON_RAW_PRES = os.path.join(DATA_RAW_DIR, "cima", "presentaciones_*.json")
PATRON_RAW_MEDS = os.path.join(DATA_RAW_DIR, "cima", "medicamentos-todos_*.json")
PATRON_TS = re.compile(r"_(\d{8}_\d{6})\.json$")


def _ultimo_snapshot() -> str:
    """Devuelve la ruta del JSON raw más reciente, priorizando el snapshot de presentaciones."""
    archivos = sorted(glob.glob(PATRON_RAW_PRES))
    if not archivos:
        archivos = sorted(glob.glob(PATRON_RAW_MEDS))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos JSON raw que coincidan en {os.path.join(DATA_RAW_DIR, 'cima')}")
    return archivos[-1]


def _leer_registros(ruta: str) -> list[dict]:
    """Lee el JSON raw; acepta la lista directa o la respuesta paginada de CIMA."""
    with open(ruta, encoding="utf-8") as f:
        contenido = json.load(f)
    if isinstance(contenido, dict):
        return contenido.get("resultados", contenido.get("presentaciones", [contenido]))
    return contenido


def _descargar_snapshot() -> str:
    inicio = time.perf_counter()
    total_esperado = get_medicamentos_pagina(1).totalFilas
    print(f"Total esperado según CIMA: {total_esperado}")

    meds = get_todos_medicamentos()
    duracion = time.perf_counter() - inicio

    ruta = guardar_modelos(meds, "medicamentos_todos")

    nregistros = [m.nregistro for m in meds]
    unicos = len(set(nregistros))
    duplicados = len(nregistros) - unicos

    print(f"\nDescargados: {len(meds)} / {total_esperado}")
    print(f"nregistro únicos: {unicos} (duplicados: {duplicados})")
    print(f"Tiempo: {duracion:.1f} s")
    print(f"Guardado en: {ruta}")

    if len(meds) != total_esperado:
        print("AVISO: el número descargado no coincide con totalFilas")
    if duplicados:
        print("AVISO: hay nregistro duplicados; revisar la paginación")

    return ruta


def _guardar_processed(df: pd.DataFrame, n_registros: int, ts: str) -> str:
    """Guarda el JSON aplanado (antes de limpiar) en processed/, con el timestamp del snapshot."""
    if len(df) != n_registros:
        raise ValueError(f"Se han perdido o duplicado filas: {n_registros} en JSON, {len(df)} en DataFrame")
    return guardar_csv(df, "medicamentos-todos", carpeta=DATA_PROCESSED_DIR, timestamp=ts)


def main() -> None:
    ruta_json = _ultimo_snapshot()
    m = PATRON_TS.search(ruta_json)
    if not m:
        raise ValueError(f"El nombre no contiene timestamp: {ruta_json}")
    ts = m.group(1)
    print(f"Snapshot seleccionado: {os.path.basename(ruta_json)}")

    registros = _leer_registros(ruta_json)
    
    # Mapear la estructura original de CIMA
    df = extraer_medicamentos(registros)

    # Si el JSON incluye 'cn' directamente (snapshots de presentaciones) y extraer_medicamentos no lo capturó:
    if "cn" not in df.columns and isinstance(registros, list) and len(registros) > 0 and "cn" in registros[0]:
        df["cn"] = [r.get("cn") for r in registros]

    # Rellenar cualquier columna faltante requerida por MAPA_COLUMNAS con valor None
    for col_origen in MAPA_COLUMNAS.keys():
        if col_origen not in df.columns:
            df[col_origen] = None

    df = limpiar_medicamentos(df, datetime.strptime(ts, "%Y%m%d_%H%M%S"))

    # Guardar CSV con timestamp y copia fija para el entrenamiento
    ruta_ts = guardar_csv(df, "medicamentos-limpios", carpeta=DATA_CLEANED_DIR, timestamp=ts)
    
    ruta_estandar = os.path.join(DATA_CLEANED_DIR, "presentaciones.csv")
    df.to_csv(ruta_estandar, sep=";", index=False)

    print(f"\nProceso finalizado. Archivos generados en data/cleaned:\n - {ruta_ts}\n - {ruta_estandar}")


if __name__ == "__main__":
    main()