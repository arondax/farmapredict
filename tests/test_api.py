"""Tests de la API con datos de ejemplo (no necesitan los snapshots reales)."""
import pytest
from fastapi.testclient import TestClient

from src.backend import datos, servicios
from src.backend.main import app


def _pres(cn, nreg, nombre, lab, dcp_id, dcp_nombre, pa, comerc=True):
    return {
        "cn": cn, "nregistro": nreg, "nombre": nombre, "laboratorio": lab,
        "comercializado": comerc, "dcp_id": dcp_id, "dcp_nombre": dcp_nombre,
        "principio_activo": pa,
    }


PRES = {
    "917070": _pres("917070", "59377", "BECLOFORTE 250 microgramos/inhalación", "GSK",
                    "770276003", "Beclometasona 250 microgramos/dosis inhalación pulmonar", "beclometasona"),
    "714479": _pres("714479", "11111", "BECLO-ASMA 100 MICROGRAMOS/PULSACION", "Aldo Union",
                    "770276002", "Beclometasona 100 microgramos/dosis inhalación pulmonar", "beclometasona"),
    "100001": _pres("100001", "30001", "IBUPROFENO A 600 mg", "Lab A", "5", "Ibuprofeno 600 mg", "ibuprofeno"),
    "100002": _pres("100002", "30002", "IBUPROFENO B 600 mg", "Lab B", "5", "Ibuprofeno 600 mg", "ibuprofeno"),
    "100003": _pres("100003", "30003", "IBUPROFENO C 600 mg", "Lab C", "5", "Ibuprofeno 600 mg", "ibuprofeno"),
}

PROBLEMAS = {
    "917070": {"tipo": 5, "fecha_inicio": "2026-11-04", "fecha_fin_prevista": None, "observaciones": "x"},
    "100003": {"tipo": 4, "fecha_inicio": "2026-10-01", "fecha_fin_prevista": None, "observaciones": "y"},
}

VIAS = {
    "59377": frozenset({"VÍA INHALATORIA"}),
    "11111": frozenset({"VÍA INHALATORIA"}),
}

RIESGO_917070 = {
    "cn": "917070", "riesgo": 0.12, "nivel": "bajo", "horizonte_dias": 30,
    "modelo": "regresion_logistica_v0", "fecha_calculo": "2026-11-09",
}


@pytest.fixture
def client(monkeypatch):
    indice = {}
    for cn, p in PRES.items():
        indice.setdefault(p["dcp_id"], []).append(cn)

    monkeypatch.setattr(datos, "cargar_presentaciones", lambda: PRES)
    monkeypatch.setattr(datos, "cargar_problemas_activos", lambda: PROBLEMAS)
    monkeypatch.setattr(datos, "indice_por_dcp", lambda: indice)
    monkeypatch.setattr(datos, "cargar_vias", lambda: VIAS)
    monkeypatch.setattr(datos, "cargar_riesgo", lambda: None)
    monkeypatch.setattr(datos, "fechas_datos",
                        lambda: {"presentaciones": "2026-11-05", "psuministro": "2026-11-05"})
    servicios._nombres_normalizados.cache_clear()
    with TestClient(app) as c:
        yield c
    servicios._nombres_normalizados.cache_clear()


# --- /health ---
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["modelo_disponible"] is False


# --- /medicamentos (búsqueda) ---
def test_buscar_encuentra_becloforte(client):
    r = client.get("/medicamentos", params={"q": "becloforte"})
    assert r.status_code == 200
    assert [m["cn"] for m in r.json()] == ["917070"]
    assert r.json()[0]["problema_activo"] is True


def test_buscar_sin_tildes_ni_mayusculas(client):
    r = client.get("/medicamentos", params={"q": "BECLOFORTE 250 microgramos/inhalacion"})
    assert r.status_code == 200 and len(r.json()) == 1


def test_buscar_q_corta_da_422(client):
    assert client.get("/medicamentos", params={"q": "ab"}).status_code == 422


def test_buscar_limite_fuera_de_rango_da_422(client):
    assert client.get("/medicamentos", params={"q": "ibuprofeno", "limite": 0}).status_code == 422


# --- /medicamentos/{cn} ---
def test_ficha_con_problema(client):
    r = client.get("/medicamentos/917070")
    assert r.status_code == 200
    j = r.json()
    assert j["cn"] == "917070"
    assert j["dcp"]["id"] == "770276003"
    assert j["problema_suministro"]["tipo"] == 5
    assert j["problema_suministro"]["fecha_inicio"] == "2026-11-04"


def test_ficha_sin_problema(client):
    assert client.get("/medicamentos/100001").json()["problema_suministro"] is None


def test_ficha_cn_inexistente_da_404(client):
    r = client.get("/medicamentos/000000")
    assert r.status_code == 404
    assert r.json()["detail"] == "CN no encontrado"


# --- /medicamentos/{cn}/sustitutos ---
def test_sustitutos_equivalentes_excluye_no_disponibles(client):
    j = client.get("/medicamentos/100001/sustitutos").json()
    # 100002 es equivalente; 100003 tiene problema activo y no cuenta
    assert [s["cn"] for s in j["sustitutos"]] == ["100002"]


def test_sustitutos_becloforte_solo_alternativas(client):
    j = client.get("/medicamentos/917070/sustitutos").json()
    assert j["sustitutos"] == []
    assert [a["cn"] for a in j["alternativas"]] == ["714479"]
    assert j["vias"] == ["VÍA INHALATORIA"]


def test_sustitutos_cn_inexistente_da_404(client):
    assert client.get("/medicamentos/000000/sustitutos").status_code == 404


# --- /medicamentos/{cn}/riesgo ---
def test_riesgo_sin_modelo_da_503(client):
    assert client.get("/medicamentos/917070/riesgo").status_code == 503


def test_riesgo_ok(client, monkeypatch):
    monkeypatch.setattr(datos, "cargar_riesgo", lambda: {"917070": RIESGO_917070})
    r = client.get("/medicamentos/917070/riesgo")
    assert r.status_code == 200
    assert r.json()["nivel"] == "bajo"


def test_riesgo_cn_sin_prediccion_da_404(client, monkeypatch):
    monkeypatch.setattr(datos, "cargar_riesgo", lambda: {"917070": RIESGO_917070})
    r = client.get("/medicamentos/100001/riesgo")
    assert r.status_code == 404
    assert r.json()["detail"] == "Sin predicción de riesgo para este CN"


def test_riesgo_cn_inexistente_da_404(client):
    assert client.get("/medicamentos/000000/riesgo").status_code == 404