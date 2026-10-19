#Clase enfocada en la API de CIMA (AEMPS) 
# para obtener información sobre medicamentos y productos sanitarios.



import time

import requests

from . import esquemas_respuesta as schemas
from .almacenamiento import guardar_modelos
from src.config import CIMA_BASE_URL

TIMEOUT = 10  # segundos
PAUSA_PAGINAS = 0.5  # segundos entre peticiones de páginas para no saturar la API

#Funciones de utilidad

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

#Funciones principales de la API

def get_medicamentos_pagina(pagina: int = 1, params: dict | None = None) -> schemas.MedicamentosResponse:
    """Devuelve una página del listado de medicamentos de CIMA."""
    url = f"{CIMA_BASE_URL}/medicamentos"
    query = {"pagina": pagina, **(params or {})}

    response = requests.get(url, params=query, timeout=TIMEOUT)
    response.raise_for_status()
    
    return schemas.MedicamentosResponse.model_validate(response.json())

def get_todos_medicamentos() -> list[schemas.Medicamento]:
    """Devuelve todos los medicamentos de CIMA, recorriendo todas las páginas."""
    return _get_paginado()

def get_medicamentos_nombre(nombre: str) -> list[schemas.Medicamento]:
    """Devuelve los medicamentos cuyo nombre coincide (parcialmente) con `nombre`."""
    return _get_paginado({"nombre": nombre})

if __name__ == "__main__":
    # Prueba rápida con una búsqueda pequeña antes de descargar el catálogo completo
    meds = get_medicamentos_nombre("ibuprofeno")
    ruta = guardar_modelos(meds, "medicamentos_ibuprofeno")
    print(f"Guardados {len(meds)} medicamentos en {ruta}")




        
       
    