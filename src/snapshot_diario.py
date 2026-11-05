"""Snapshot diario de /psuministro (raw). Idempotente: si ya hay uno de hoy, no hace nada."""
from src.api.api import get_psuministro_raw
from src.api.almacenamiento import guardar_raw, snapshot_del_dia

NOMBRE = "psuministro"


def main() -> None:
    existente = snapshot_del_dia(NOMBRE)
    if existente:
        print(f"Ya existe el snapshot de hoy: {existente}")
        return
    registros = get_psuministro_raw()
    print(f"{len(registros)} registros -> {guardar_raw(registros, NOMBRE)}")


if __name__ == "__main__":
    main()