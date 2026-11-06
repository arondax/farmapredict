"""
Tabla de incidencias de suministro: una fila por episodio (cn, fecha_inicio).

Une dos fuentes:
- Backfill (05/11): último episodio de cada CN, con fecha de fin real si está resuelto.
- Snapshots diarios (desde 04/11): todos los episodios activos de cada día. Un episodio
  termina en el primer snapshot en el que ya no aparece.
"""

#TODO MODIFICAR PARA QUE SE HAGA DESDE EL CSV LIMPIO, PARA AGILIZAR TRABAJO LO HACEMOS DESDE LOS DATOS RAW, PERO HAY QUE LIMPIAR EL CSV Y HACERLO DESDE EL CSV LIMPIO
from datetime import date, datetime
from zoneinfo import ZoneInfo

#import pandas as pd

ZONA = ZoneInfo("Europe/Madrid")
COLUMNAS = ["cn", "fecha_inicio", "fecha_fin", "tipo", "activa", "origen", "fin_por_desaparicion"]


def _fecha(ms: int | None) -> date | None:
    """Epoch en ms de CIMA -> fecha en hora de Madrid."""
    return datetime.fromtimestamp(ms / 1000, tz=ZONA).date() if ms else None


def _desde_snapshots(snapshots: dict[date, list[dict]]) -> dict[tuple, dict]:
    """(cn, fecha_inicio) -> {tipo, fecha_fin, activa} a partir de snapshots consecutivos."""
    fechas = sorted(snapshots)
    ultimo = fechas[-1]
    vistos: dict[tuple, dict] = {}

    for fecha in fechas:
        for r in snapshots[fecha]:
            clave = (str(r["cn"]), _fecha(r.get("fini")))
            info = vistos.setdefault(clave, {"tipo": r.get("tipoProblemaSuministro"), "ultima_vez": fecha})
            info["ultima_vez"] = fecha
            info["tipo"] = r.get("tipoProblemaSuministro")  # el tipo del snapshot más reciente

    resultado = {}
    for clave, info in vistos.items():
        if info["ultima_vez"] == ultimo:
            resultado[clave] = {"tipo": info["tipo"], "fecha_fin": None, "activa": True}
        else:
            # fin = primer snapshot posterior a la última aparición
            fin = next(f for f in fechas if f > info["ultima_vez"])
            resultado[clave] = {"tipo": info["tipo"], "fecha_fin": fin, "activa": False}
    return resultado


def _desde_backfill(backfill: list[dict]) -> dict[tuple, dict]:
    """(cn, fecha_inicio) -> {tipo, fecha_fin, activa} a partir del backfill."""
    resultado = {}
    for linea in backfill:
        r = linea["respuesta"]
        if "fini" not in r:  # CN sin problemas registrados
            continue
        clave = (str(linea["cn"]), _fecha(r["fini"]))  # el cn de fuera: el de dentro viene como int
        activa = bool(r.get("activo"))
        resultado[clave] = {
            "tipo": r.get("tipoProblemaSuministro"),
            "fecha_fin": None if activa else _fecha(r.get("ffin")),  # ffin solo es real si está resuelto
            "activa": activa,
        }
    return resultado


def construir_incidencias(snapshots: dict[date, list[dict]], backfill: list[dict]) -> list[dict]:
    """
    Une snapshots y backfill en una tabla de episodios.

    Prioridad para la fecha de fin:
    1. Si sigue en el último snapshot -> activa (manda el dato más reciente).
    2. Si el backfill la da por resuelta -> fecha de fin real del backfill.
    3. Si desapareció de los snapshots -> fecha del primer snapshot sin ella.
    """
    snap = _desde_snapshots(snapshots)
    bf = _desde_backfill(backfill)

    filas = []
    for clave in snap.keys() | bf.keys():
        s, b = snap.get(clave), bf.get(clave)
        origen = "ambos" if s and b else ("snapshots" if s else "backfill")

        if s and s["activa"]:
            fecha_fin, activa, por_desaparicion = None, True, False
        elif b and not b["activa"]:
            fecha_fin, activa, por_desaparicion = b["fecha_fin"], False, False
        elif s:
            fecha_fin, activa, por_desaparicion = s["fecha_fin"], False, True
        else:
            # Activa en el backfill y nunca vista en snapshots: no debería ocurrir
            fecha_fin, activa, por_desaparicion = None, True, False

        filas.append({
            "cn": clave[0],
            "fecha_inicio": clave[1],
            "fecha_fin": fecha_fin,
            "tipo": (s or b)["tipo"],
            "activa": activa,
            "origen": origen,
            "fin_por_desaparicion": por_desaparicion,
        })

    filas.sort(key=lambda f: (f["cn"], f["fecha_inicio"]))
    return filas