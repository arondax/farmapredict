"""Snapshot (raw) de endpoints paginados de CIMA. Idempotente por día.

python -m src.snapshot_diario                 -> psuministro
python -m src.snapshot_diario presentaciones
"""
import sys

from src.api.api import get_paginado_raw
from src.api.almacenamiento import guardar_raw, snapshot_del_dia


def snapshot(nombre: str) -> str:
    existente = snapshot_del_dia(nombre)
    if existente:
        print(f"Ya existe el snapshot de hoy: {existente}")
        return existente
    registros = get_paginado_raw(nombre)
    ruta = guardar_raw(registros, nombre)
    print(f"{nombre}: {len(registros)} registros -> {ruta}")
    return ruta


def main() -> None:
    for nombre in sys.argv[1:] or ["psuministro"]:
        snapshot(nombre)


if __name__ == "__main__":
    main()