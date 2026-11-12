"""Lógica de negocio del backend: búsqueda, ficha y sustitutos. Sin HTTP ni acceso a ficheros."""
import unicodedata
from functools import lru_cache

from src.backend import datos

# Fuente: CIMA REST API – Problemas de suministro (AEMPS, 2019). Los códigos 10-12 no están documentados.
TIPOS_PROBLEMA = {
    1: "Consultar nota informativa",
    2: "Suministro solo a hospitales",
    3: "El médico prescriptor deberá valorar otros tratamientos comercializados",
    4: "Desabastecimiento temporal",
    5: "Existen otros medicamentos con el mismo principio activo y vía de administración",
    6: "Existen otros medicamentos con los mismos principios activos y vía de administración",
    7: "Se puede solicitar como medicamento extranjero",
    8: "Se recomienda restringir su prescripción a casos sin alternativa",
    9: "Distribución controlada por unidades limitadas",
}

CRITERIO_SUSTITUTOS = "mismo DCP, comercializado, sin problema de suministro activo"


def _normalizar(texto: str | None) -> str:
    """Minúsculas y sin tildes, para buscar 'ACIDO' y encontrar 'ácido'."""
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower()


@lru_cache(maxsize=1)
def _nombres_normalizados() -> list[tuple[str, str]]:
    """(cn, nombre normalizado) para todas las presentaciones; se calcula una vez."""
    return [(cn, _normalizar(p["nombre"])) for cn, p in datos.cargar_presentaciones().items()]


def _resumen(p: dict) -> dict:
    return {
        "cn": p["cn"],
        "nombre": p["nombre"],
        "laboratorio": p["laboratorio"],
        "comercializado": p["comercializado"],
        "problema_activo": p["cn"] in datos.cargar_problemas_activos(),
    }


def buscar(texto: str, limite: int = 20) -> list[dict]:
    """Presentaciones cuyo nombre contiene `texto`. Primero las comercializadas."""
    consulta = _normalizar(texto).strip()
    if len(consulta) < 3:
        return []
    presentaciones = datos.cargar_presentaciones()
    encontrados = [presentaciones[cn] for cn, nombre in _nombres_normalizados() if consulta in nombre]
    encontrados.sort(key=lambda p: (
    not p["comercializado"],
    not _normalizar(p["nombre"]).startswith(consulta),
    p["nombre"] or "",
))
    return [_resumen(p) for p in encontrados[:limite]]


def ficha(cn: str) -> dict | None:
    """Ficha de una presentación con su problema activo, o None si el CN no existe."""
    p = datos.cargar_presentaciones().get(cn)
    if p is None:
        return None

    problema = datos.cargar_problemas_activos().get(cn)
    if problema is not None:
        problema = {**problema, "descripcion": TIPOS_PROBLEMA.get(problema["tipo"], "Tipo sin documentar")}

    return {
        "cn": p["cn"],
        "nregistro": p["nregistro"],
        "nombre": p["nombre"],
        "laboratorio": p["laboratorio"],
        "dcp": {"id": p["dcp_id"], "nombre": p["dcp_nombre"]},
        "principio_activo": p["principio_activo"],
        "comercializado": p["comercializado"],
        "problema_suministro": problema,
    }


CRITERIO_SUSTITUTOS = "mismo DCP (principio activo, dosis y forma), comercializado, sin problema de suministro activo"
CRITERIO_ALTERNATIVAS = (
    "mismo principio activo y misma vía de administración, con otra dosis o forma; "
    "comercializado y sin problema activo. Requiere valoración del farmacéutico o del médico"
)


def _disponible(cn: str) -> bool:
    return datos.cargar_presentaciones()[cn]["comercializado"] and cn not in datos.cargar_problemas_activos()


def sustitutos(cn: str) -> dict | None:
    """Sustitutos equivalentes (mismo DCP) y alternativas a valorar (mismo principio activo y vía)."""
    presentaciones = datos.cargar_presentaciones()
    p = presentaciones.get(cn)
    if p is None:
        return None

    # 1. Equivalentes: mismo DCP
    mismo_dcp = datos.indice_por_dcp().get(p["dcp_id"], []) if p["dcp_id"] else []
    equivalentes = [presentaciones[c] for c in mismo_dcp if c != cn and _disponible(c)]

    # 2. Alternativas: mismo principio activo, alguna vía en común, otro DCP
    vias = datos.cargar_vias()
    vias_origen = vias.get(p["nregistro"], frozenset())
    alternativas = []
    if p["principio_activo"] and vias_origen:
        alternativas = [
            q for q in presentaciones.values()
            if q["principio_activo"] == p["principio_activo"]
            and q["dcp_id"] != p["dcp_id"]
            and vias.get(q["nregistro"], frozenset()) & vias_origen
            and _disponible(q["cn"])
        ]

    def _salida(lista: list[dict]) -> list[dict]:
        lista = sorted(lista, key=lambda s: s["nombre"] or "")
        return [{"cn": s["cn"], "nombre": s["nombre"], "laboratorio": s["laboratorio"], "dcp": s["dcp_nombre"]} for s in lista]

    return {
        "cn": cn,
        "dcp": {"id": p["dcp_id"], "nombre": p["dcp_nombre"]},
        "vias": sorted(vias_origen),
        "sustitutos": _salida(equivalentes),
        "criterio_sustitutos": CRITERIO_SUSTITUTOS,
        "alternativas": _salida(alternativas),
        "criterio_alternativas": CRITERIO_ALTERNATIVAS,
    }
class ModeloNoDisponible(Exception):
    """El fichero de riesgo todavía no existe."""


def riesgo(cn: str) -> dict | None:
    tabla = datos.cargar_riesgo()
    if tabla is None:
        raise ModeloNoDisponible
    return tabla.get(cn)