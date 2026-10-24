#Clase para HARDCODEAR las rutas de los archivos

import os

# URL base de la API pública de CIMA (AEMPS). No requiere API key.
# Se deja hardcodeada porque no es un secreto y es igual en todos los entornos.
# TODO: si se necesita sobrescribir (p. ej. mock server en tests o cambio de
# versión de la API), pasar a configuración híbrida:
#   CIMA_BASE_URL = os.getenv("CIMA_BASE_URL", "https://cima.aemps.es/cima/rest")
# y añadir `# CIMA_BASE_URL=...` comentada en .env.example.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CIMA_BASE_URL = "https://cima.aemps.es/cima/rest"
DATA_PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")