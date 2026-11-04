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
from src.api.limpieza_medicamentos import limpiar_medicamentos

PATRON_RAW = os.path.join(DATA_RAW_DIR, "cima", "medicamentos-todos_*.json")
PATRON_TS = re.compile(r"_(\d{8}_\d{6})\.json$")


def _ultimo_snapshot() -> str:
    """Devuelve la ruta del JSON raw más reciente (el timestamp del nombre ordena)."""
    archivos = sorted(glob.glob(PATRON_RAW))
    if not archivos:
        raise FileNotFoundError(f"No hay archivos que coincidan con {PATRON_RAW}")
    return archivos[-1]


def _leer_registros(ruta: str) -> list[dict]:
    """Lee el JSON raw; acepta la lista directa o la respuesta paginada de CIMA."""
    with open(ruta, encoding="utf-8") as f:
        contenido = json.load(f)
    return contenido["resultados"] if isinstance(contenido, dict) else contenido

def _descargar_snapshot() -> str:
    inicio = time.perf_counter()

    # Total esperado según la API, para compararlo al final
    total_esperado = get_medicamentos_pagina(1).totalFilas
    print(f"Total esperado según CIMA: {total_esperado}")

    meds = get_todos_medicamentos()
    duracion = time.perf_counter() - inicio

    ruta = guardar_modelos(meds, "medicamentos_todos")

    # --- Comprobaciones ---
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
    print(f"Snapshot: {os.path.basename(ruta_json)}")

    registros = _leer_registros(ruta_json)
    df = extraer_medicamentos(registros)
    df = limpiar_medicamentos(df, datetime.strptime(ts, "%Y%m%d_%H%M%S"))

    ruta = guardar_csv(df, "medicamentos_limpios", carpeta=DATA_CLEANED_DIR, timestamp=ts)
    print(f"Guardado en: {ruta}")


if __name__ == "__main__":
    main()