#Clase enfocada en la API de CIMA (AEMPS) 
# para obtener información sobre medicamentos y productos sanitarios.

import requests
import json
import time
import os
import config
from . import esquemas_respuesta as schemas
from config import CIMA_BASE_URL

TIMEOUT = 10  # segundos

def get_medicamentos_pagina(pagina: int = 1) -> schemas.MedicamentosResponse:
    """Devuelve una página del listado de medicamentos de CIMA."""
    url = f"{CIMA_BASE_URL}/medicamentos"
    params = {"pagina": pagina}

    response = requests.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    
    return schemas.MedicamentosResponse.model_validate(response.json())

def get_todos_medicamentos() -> list[schemas.Medicamento]:
    """Recorre todas las páginas y devuelve la lista completa."""
    medicamentos: list[schemas.Medicamento] = []
    pagina = 1

    while True:
        data = get_medicamentos_pagina(pagina)

        if not data.resultados:
            break

        medicamentos.extend(data.resultados)
        print(f"Página {pagina}: {len(medicamentos)}/{data.totalFilas}")

        if len(medicamentos) >= data.totalFilas:
            break
        pagina += 1

    return medicamentos

if __name__ == "__main__":
    # Prueba rápida: solo la primera página
    data = get_medicamentos_pagina(1)
    print(f"Total en CIMA: {data.totalFilas}")
    for med in data.resultados[:5]:
        print(med.nregistro, "-", med.nombre)




        
       
    