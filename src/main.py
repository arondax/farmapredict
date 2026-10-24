# src/main.py
import glob
import json
import os

from src.config import DATA_RAW_DIR

patron = os.path.join(DATA_RAW_DIR, "cima", "medicamentos-todos_*.json")
archivos = sorted(glob.glob(patron))

if not archivos:
    raise FileNotFoundError(f"No hay archivos que coincidan con {patron}")

ruta = archivos[-1]  # el timestamp en el nombre hace que el último sea el más reciente
print(f"Validando: {ruta}")

with open(ruta, encoding="utf-8") as f:
    datos = json.load(f)

print(f"Registros: {len(datos)}")