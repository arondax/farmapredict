#Clase enfocada en la API de CIMA (AEMPS) 
# para obtener información sobre medicamentos y productos sanitarios.



import time

import requests
from urllib3 import Retry

from . import esquemas_respuesta as schemas
from .almacenamiento import guardar_modelos
from src.config import CIMA_BASE_URL

TIMEOUT = 30  # segundos
PAUSA_PAGINAS = 0.5  # segundos entre peticiones de páginas para no saturar la API

#Funciones de utilidad
def _cerrar_sesion() -> requests.Session:
    """Sesión HTTP reutilizable con reintentos y backoff exponencial (1s, 2s, 4s...)."""
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=("GET",),
    )
    sesion = requests.Session()
    sesion.mount("https://", HTTPAdapter(max_retries=retry))
    sesion.headers["Accept"] = "application/json"
    return sesion

_SESION = _cerrar_sesion()

def _get_json(endpont: str, params: dict | None = None):
    """GET a CIMA y devuelve el JSON tal cual, sin validar."""
    url = f"{CIMA_BASE_URL}/{endpoint.lstrip('/')}"
    response = _SESION.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

def _get_paginado(params: dict | None = None) -> list[schemas.Medicamento]:
    """Recorre todas las páginas de /medicamentos con los filtros dados."""
    medicamentos: list[schemas.Medicamento] = []
    pagina = 1

    while True:
        data = get_medicamentos_pagina(pagina, params)
        if not data.resultados:
            break

        medicamentos.extend(data.resultados)
        print(f"Página {pagina}: {len(medicamentos)}/{data.totalFilas}")

        if len(medicamentos) >= data.totalFilas:
            break
        pagina += 1
        time.sleep(PAUSA_PAGINAS)

    return medicamentos

def get_paginado_raw(endpoint: str, params: dict | None = None) -> list[dict]:
    """
    Recorre todas las páginas de un endpoint de CIMA y devuelve los registros
    sin validar (capa raw). Si el endpoint no pagina y devuelve una lista, la
    devuelve directamente.
    """
    params = dict(params or {})
    registros: list[dict] = []
    pagina = 1

    while True:
        params["pagina"] = pagina
        data = _get_json(endpoint, params)

        if isinstance(data, list):
            return data

        resultados = data.get("resultados") or []
        registros.extend(resultados)
        total = data.get("totalFilas", 0)
        print(f"{endpoint} | página {pagina}: {len(registros)}/{total}")

        if not resultados or len(registros) >= total:
            return registros
        pagina += 1
        time.sleep(PAUSA_PAGINAS)

#Funciones principales de la API

def get_medicamentos_pagina(pagina: int = 1, params: dict | None = None) -> schemas.MedicamentosResponse:
    """Devuelve una página del listado de medicamentos de CIMA."""
    query = {"pagina": pagina, **(params or {})}
    return schemas.MedicamentosResponse.model_validate(_get_json("medicamentos", query))

def get_todos_medicamentos() -> list[schemas.Medicamento]:
    """Devuelve todos los medicamentos de CIMA, recorriendo todas las páginas."""
    return _get_paginado()

def get_medicamentos_nombre(nombre: str) -> list[schemas.Medicamento]:
    """Devuelve los medicamentos cuyo nombre coincide (parcialmente) con `nombre`."""
    return _get_paginado({"nombre": nombre})

def get_psuministro_raw() -> list[dict]:
    """Todas las incidencias de suministro que devuelva CIMA, sin validar."""
    return get_paginado_raw("psuministro")



        
       
    