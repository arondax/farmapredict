import os
import pandas as pd

# Obtener la ruta de la carpeta donde se encuentra este archivo .py
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(DIRECTORIO_ACTUAL, "medicamentos-todos.csv")

# Ingesta del archivo
df = pd.read_csv(RAW_PATH, sep=";", dtype=str)
OUTPUT_PATH = "medicamentos_limpios.csv"

print("🔍 Cargando medicamentos-todos.csv...")
df = pd.read_csv(RAW_PATH, sep=";", dtype=str)

# 1. Renombrar y estandarizar columnas para FarmaPredict
mapa = {
    "nregistro": "nregistro",
    "nombre": "nombre_medicamento",
    "vtm": "principio_activo",
    "dosis": "dosis",
    "forma_farmaceutica": "forma_farmaceutica",
    "vias": "via_administracion",
    "labtitular": "laboratorio",
    "cpresc": "condiciones_prescripcion",
    "comerc": "es_comercializado",
    "receta": "requiere_receta",
    "generico": "es_generico",
    "psum": "problema_suministro",
    "fecha_aut": "fecha_autorizacion",
    "fecha_rev": "fecha_revision",
}
df = df.rename(columns=mapa)

# 2. Reordenar columnas en bloque lógico
orden = [
    "nregistro",
    "nombre_medicamento",
    "principio_activo",
    "dosis",
    "forma_farmaceutica",
    "via_administracion",
    "laboratorio",
    "condiciones_prescripcion",
    "es_comercializado",
    "requiere_receta",
    "es_generico",
    "problema_suministro",
    "fecha_autorizacion",
    "fecha_revision",
]
df = df[orden]

# 3. Limpiar espacios y pasar a mayúsculas
for col in df.columns:
  df[col] = df[col].astype(str).str.strip().replace(["nan", "None", ""], None)

df["principio_activo"] = df["principio_activo"].str.upper()
df["forma_farmaceutica"] = df["forma_farmaceutica"].str.upper()

# 4. Eliminar duplicados por nregistro
df = df.drop_duplicates(subset=["nregistro"])

# 5. Guardar el resultado ordenado
df.to_csv(OUTPUT_PATH, index=False, sep=";", encoding="utf-8")
print(
    f"✅ ¡Hecho! Archivo guardado como '{OUTPUT_PATH}' con {len(df)} registros."
)

import unicodedata
import os
import pandas as pd

# 1. Cargar el dataset que acabas de ordenar
df = pd.read_csv("medicamentos_limpios.csv", sep=";", dtype=str)

print("🛡️ Sanitizando datos para compatibilidad total con la API REST...")

# Función para quitar tildes de textos de búsqueda
def quitar_tilde(texto):
  if not isinstance(texto, str):
    return ""
  return "".join(
      c
      for c in unicodedata.normalize("NFD", texto)
      if unicodedata.category(c) != "Mn"
  )


# --- PASO A: Limpieza de caracteres invisibles y saltos de línea ---
columnas_texto = df.select_dtypes(include="object").columns
for col in columnas_texto:
  df[col] = (
      df[col]
      .astype(str)
      .str.replace(r"[\r\n\t]", " ", regex=True)  # Elimina saltos de línea
      .str.strip()  # Elimina espacios al inicio y final
      .str.replace(r"\s+", " ", regex=True)
  )  # Elimina espacios dobles

# --- PASO B: Control de ceros a la izquierda en identificadores ---
if "nregistro" in df.columns:
  df["nregistro"] = df["nregistro"].astype(str).str.zfill(6)

# --- PASO C: Normalización canónica para el recomendador de sustitutivos ---
if "principio_activo" in df.columns:
  df["principio_activo_norm"] = (
      df["principio_activo"].apply(quitar_tilde).str.upper()
  )

if "forma_farmaceutica" in df.columns:
  df["forma_farmaceutica_norm"] = (
      df["forma_farmaceutica"].apply(quitar_tilde).str.upper()
  )

# --- PASO D: Conversión estricta de booleanos ---
cols_bool = [
    "es_comercializado",
    "requiere_receta",
    "es_generico",
    "problema_suministro",
]
for col in cols_bool:
  if col in df.columns:
    df[col] = (
        df[col]
        .astype(str)
        .str.lower()
        .map({
            "true": "True",
            "false": "False",
            "1": "True",
            "0": "False",
            "si": "True",
            "no": "False",
        })
    )

# --- PASO E: Sanitización final de nulos para JSON (Evitar error 500) ---
# Reemplazamos las representaciones de nulos por cadena vacía
df = df.fillna("").replace(["nan", "NaN", "None", "<NA>"], "")

# --- PASO F: Guardar resultado final para la BD / API ---
OUTPUT_API_PATH = "medicamentos_preparados_api.csv"
df.to_csv(OUTPUT_API_PATH, index=False, sep=";", encoding="utf-8")

print(
    f"✅ ¡Completado! CSV sanitizado listo para la API guardado como:"
    f" '{OUTPUT_API_PATH}'"
)