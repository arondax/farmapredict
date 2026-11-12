"""Genera data/cleaned/incidencias.csv desde el raw.  ->  python -m src.construir_incidencias"""
import glob
import json
import os
import csv
from collections import Counter

from datetime import datetime

from src.api.incidencias import construir_incidencias, COLUMNAS
from src.config import DATA_CLEANED_DIR, DATA_RAW_DIR

CARPETA = os.path.join(DATA_RAW_DIR, "cima")


def _leer_snapshots() -> dict:
    snapshots = {}
    for ruta in sorted(glob.glob(os.path.join(CARPETA, "psuministro_*.json"))):
        fecha = datetime.strptime(os.path.basename(ruta).split("_")[1], "%Y%m%d").date()
        with open(ruta, encoding="utf-8") as f:
            snapshots[fecha] = json.load(f)
    if not snapshots:
        raise FileNotFoundError(f"No hay snapshots de psuministro en {CARPETA}")
    return snapshots


def _leer_backfill() -> list[dict]:
    rutas = sorted(glob.glob(os.path.join(CARPETA, "backfill_psuministro_*.jsonl")))
    if not rutas:
        raise FileNotFoundError(f"No hay backfill en {CARPETA}")
    with open(rutas[-1], encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def main() -> None:
    snapshots = _leer_snapshots()
    backfill = _leer_backfill()
    filas = construir_incidencias(snapshots, backfill)

    claves = [(f["cn"], f["fecha_inicio"]) for f in filas]
    assert len(claves) == len(set(claves)), "Hay episodios duplicados"
    assert all(f["fecha_fin"] >= f["fecha_inicio"] for f in filas if f["fecha_fin"]), "fecha_fin anterior a fecha_inicio"

    print(f"Snapshots: {len(snapshots)} ({min(snapshots)} a {max(snapshots)}) | backfill: {len(backfill)} CN")
    print(f"Incidencias: {len(filas)} | activas: {sum(f['activa'] for f in filas)} "
          f"(último snapshot: {len(snapshots[max(snapshots)])})")
    print("Por origen:", dict(Counter(f["origen"] for f in filas)))
    print("Fin por desaparición:", sum(f["fin_por_desaparicion"] for f in filas))

    os.makedirs(DATA_CLEANED_DIR, exist_ok=True)
    ruta = os.path.join(DATA_CLEANED_DIR, "incidencias.csv")
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Guardado en: {ruta}")
    print(f"Guardado en: {ruta}")


if __name__ == "__main__":
    main()