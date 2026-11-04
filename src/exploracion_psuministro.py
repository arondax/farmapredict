"""¿/psuministro tiene histórico o solo incidencias activas?  ->  python -m src.exploracion_psuministro"""
import json
from collections import Counter
from datetime import date, datetime, timezone

from src.api.api import get_psuministro_raw
from src.api.almacenamiento import guardar_raw, snapshot_del_dia

NOMBRE = "psuministro"


def _fecha(ms: int | None) -> date | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date() if ms else None


def main() -> None:
    ruta = snapshot_del_dia(NOMBRE)
    if ruta:
        print(f"Ya hay snapshot de hoy, se reutiliza: {ruta}")
        with open(ruta, encoding="utf-8") as f:
            registros = json.load(f)
    else:
        registros = get_psuministro_raw()
        ruta = guardar_raw(registros, NOMBRE)
        print(f"Guardado en: {ruta}")

    hoy = date.today()
    print(f"\nTotal registros: {len(registros)}")
    print("Campos (frecuencia):", dict(Counter(k for r in registros for k in r)))
    print("activo:", dict(Counter(r.get("activo") for r in registros)))

    finis = sorted(f for r in registros if (f := _fecha(r.get("fini"))))
    if finis:
        print(f"fini: de {finis[0]} a {finis[-1]}")
        print("Incidencias por año de inicio:", dict(sorted(Counter(f.year for f in finis).items())))

    ffins = [f for r in registros if (f := _fecha(r.get("ffin")))]
    print(f"ffin pasada (cerradas): {sum(f < hoy for f in ffins)} | ffin futura: {sum(f >= hoy for f in ffins)} "
          f"| sin ffin: {len(registros) - len(ffins)}")

    cns = Counter(r.get("cn") for r in registros)
    print(f"CN únicos: {len(cns)} | CN con >1 incidencia: {sum(v > 1 for v in cns.values())}")

    if registros:
        print("\nEjemplo:\n" + json.dumps(registros[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()