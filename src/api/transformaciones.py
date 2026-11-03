import os
import glob
import json
import pandas as pd
from src.api.almacenamiento import *
from src.config import *
CAMPOS_BASICOS = [
    "nregistro", "nombre", "labtitular", "cpresc", "dosis",
    "comerc", "receta", "generico", "psum",
]

COLUMNAS_FECHA = ["fecha_aut", "fecha_rev"]

#FUNCIONES

def extraer_medicamentos(registros: list[dict]) -> pd.DataFrame:
    """
    Extrae la información de los medicamentos de una lista de registros y devuelve un DataFrame.

    Args:
        registros (list[dict]): Lista de registros de medicamentos.

    Returns:
        pd.DataFrame: DataFrame con la información de los medicamentos.
    """

    filas=[]

    for med in registros:
        #Campos basicos
        fila = {campo: med.get(campo) for campo in CAMPOS_BASICOS}
        #print(f"Procesando medicamento: {fila.get('nombre')} (nregistro: {fila.get('nregistro')})")

        #Campos compuestos
        fila ["forma_farmaceutica"] = med.get("formaFarmaceuticaSimplificada" or {}).get("nombre")
        fila["vtm"] = (med.get("vtm") or {}).get("nombre")
        fila["vias"] = "|".join(v.get("nombre", "") for v in med.get("viasAdministracion") or [])

        estado = med.get("estado") or {}
        fila["fecha_aut"] = estado.get("aut")
        fila["fecha_rev"] = estado.get("rev")

        filas.append(fila)

    df = pd.DataFrame(filas)
    if df.empty:
        return df

    # Epoch en milisegundos -> datetime
    for col in COLUMNAS_FECHA:
        df[col] = pd.to_datetime(df[col], unit="ms", utc=True)

    return df
