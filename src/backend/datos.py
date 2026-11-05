"""
Acceso a datos del backend.

Hoy lee la capa raw (último snapshot de cada endpoint). Cuando exista la capa
cleaned, solo cambia el interior de este módulo: el resto del backend usa estas
funciones y no sabe de dónde vienen los datos.
"""
import glob
import json
import os
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from src.config import DATA_RAW_DIR

CARPETA_CIMA = os.path.join(DATA_RAW_DIR, "cima")
ZONA = ZoneInfo("Europe/Madrid")


# --- Utilidades ---

def _ultimo_snapshot(nombre: str) -> str:
    archivos = sorted(glob.glob(os.path.join(CARPETA_CIMA, f"{nombre}_*.json")))
    if not archivos:
        raise FileNotFoundError(
            f"No hay snapshot de '{nombre}' en {CARPETA_CIMA}. "
            f"Ejecuta: python -m src.snapshot_diario {nombre}"
        )
    return archivos[-1]


def _leer_json(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _fecha_de_nombre(ruta: str) -> str:
    """psuministro_20261105_160540.json -> '2026-11-05'"""
    fecha = os.path.basename(ruta).rsplit("_", 2)[1]
    return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"


def ms_a_fecha(ms: int | None) -> str | None:
    """Epoch en milisegundos de CIMA -> fecha ISO en hora de Madrid."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=ZONA).date().isoformat()


def _resumir_presentacion(p: dict) -> dict:
    """Solo los campos que usa el backend (el raw trae docs, fotos, excipientes...)."""
    dcp = p.get("dcp") or {}
    return {
        "cn": str(p["cn"]),
        "nregistro": str(p.get("nregistro")) if p.get("nregistro") is not None else None,
        "nombre": p.get("nombre"),
        "laboratorio": p.get("labtitular"),
        "comercializado": bool(p.get("comerc")),
        "dcp_id": str(dcp["id"]) if dcp.get("id") is not None else None,
        "dcp_nombre": dcp.get("nombre"),
        "principio_activo": (p.get("vtm") or {}).get("nombre"),
    }


# --- Carga (una vez por proceso; recargar() para refrescar) ---

@lru_cache(maxsize=1)
def cargar_presentaciones() -> dict[str, dict]:
    """CN -> presentación resumida."""
    registros = _leer_json(_ultimo_snapshot("presentaciones"))
    return {str(p["cn"]): _resumir_presentacion(p) for p in registros if p.get("cn")}


@lru_cache(maxsize=1)
def cargar_problemas_activos() -> dict[str, dict]:
    """CN -> problema de suministro activo, con fechas ya convertidas."""
    registros = _leer_json(_ultimo_snapshot("psuministro"))
    return {
        str(r["cn"]): {
            "tipo": r.get("tipoProblemaSuministro"),
            "fecha_inicio": ms_a_fecha(r.get("fini")),
            "fecha_fin_prevista": ms_a_fecha(r.get("ffin")),
            "observaciones": r.get("observ"),
        }
        for r in registros
        if r.get("activo", True)
    }


@lru_cache(maxsize=1)
def indice_por_dcp() -> dict[str, list[str]]:
    """dcp_id -> lista de CN con ese DCP (para el recomendador)."""
    indice: dict[str, list[str]] = defaultdict(list)
    for cn, p in cargar_presentaciones().items():
        if p["dcp_id"]:
            indice[p["dcp_id"]].append(cn)
    return dict(indice)


def fechas_datos() -> dict[str, str]:
    """Fecha de cada snapshot cargado (para /health)."""
    return {nombre: _fecha_de_nombre(_ultimo_snapshot(nombre)) for nombre in ("presentaciones", "psuministro")}


def recargar() -> None:
    """Vacía la caché para leer los últimos snapshots sin reiniciar el servidor."""
    for funcion in (cargar_presentaciones, cargar_problemas_activos, indice_por_dcp):
        funcion.cache_clear()