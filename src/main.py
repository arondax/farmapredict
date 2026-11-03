import glob
import json
import os
import re
from datetime import datetime

from src.config import DATA_RAW_DIR, DATA_CLEANED_DIR
from src.api.transformaciones import extraer_medicamentos
from src.api.limpieza_medicamentos import limpiar_medicamentos
from src.api.almacenamiento import guardar_csv

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