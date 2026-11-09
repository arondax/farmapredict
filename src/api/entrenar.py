import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZONTE = 30
CORTES = pd.date_range("2026-05-04", "2026-10-05", freq="7D")

# 1. Carga de datos
inc = pd.read_csv("data/cleaned/incidencias.csv", sep=";", dtype={"cn": str}, parse_dates=["fecha_inicio", "fecha_fin"])
pres_todas = pd.read_csv("data/cleaned/presentaciones.csv", dtype={"cn": str}, parse_dates=["fecha_autorizacion"])

# Asegurar fecha de autorización sin zona horaria en hora de Madrid
if pres_todas["fecha_autorizacion"].dt.tz is not None:
    pres_todas["fecha_autorizacion"] = pres_todas["fecha_autorizacion"].dt.tz_convert("Europe/Madrid").dt.tz_localize(None)

pres = pres_todas[pres_todas["comercializado"]].copy()

# Features estáticas
pres["n_alt_dcp"] = pres.groupby("dcp_id")["cn"].transform("count")
pres["n_alt_vtm"] = pres.groupby("vtm_id")["cn"].transform("count") - 1
pres["n_labs_vtm"] = pres.groupby("vtm_id")["laboratorio"].transform("nunique")
pres["no_sustituible"] = (pres["nosustituible_id"] != 0).astype(int)

CONTEOS = ["n_alt_dcp", "n_alt_vtm", "n_labs_vtm", "inc_lab_90d", "inc_vtm_90d", "activas_vtm_t", "activas_dcp_t"]
BINARIAS = ["generico", "huerfano", "biosimilar", "receta", "ema", "envase_clinico", "no_sustituible"]
FEATURES = CONTEOS + BINARIAS + ["antiguedad_anios"]

def filas_corte(t: pd.Timestamp) -> pd.DataFrame:
    activas = inc[(inc.fecha_inicio <= t) & (inc.fecha_fin.isna() | (inc.fecha_fin > t))]
    nuevas = inc[(inc.fecha_inicio > t) & (inc.fecha_inicio <= t + pd.Timedelta(days=HORIZONTE))]
    previas = inc[(inc.fecha_inicio <= t) & (inc.fecha_inicio > t - pd.Timedelta(days=90))]

    df = pres[~pres.cn.isin(activas.cn)].copy()
    df["fecha_corte"] = t
    df["y"] = df.cn.isin(nuevas.cn).astype(int)

    info = pres_todas[["cn", "laboratorio", "vtm_id", "dcp_id"]]
    prev = previas.merge(info, on="cn")
    act = activas.merge(info, on="cn")

    df["inc_lab_90d"] = df.laboratorio.map(prev.laboratorio.value_counts()).fillna(0)
    df["inc_vtm_90d"] = df.vtm_id.map(prev.vtm_id.value_counts()).fillna(0)
    df["activas_vtm_t"] = df.vtm_id.map(act.vtm_id.value_counts()).fillna(0)
    df["activas_dcp_t"] = df.dcp_id.map(act.dcp_id.value_counts()).fillna(0)
    df["antiguedad_anios"] = (t - df.fecha_autorizacion).dt.days / 365.25

    for c in CONTEOS:
        df[c] = np.log1p(df[c])

    df[BINARIAS] = df[BINARIAS].fillna(False).astype(int)
    df["antiguedad_anios"] = df["antiguedad_anios"].fillna(df["antiguedad_anios"].median())
    return df

# 2. Generación del dataset
dataset = pd.concat([filas_corte(t) for t in CORTES], ignore_index=True)
print(f"Dataset generado: {len(dataset)} filas | Prevalencia: {dataset.y.mean():.4f}")

# 3. Split temporal
inicio_test = CORTES[-4]
limite_train = inicio_test - pd.Timedelta(days=HORIZONTE)

train = dataset[dataset.fecha_corte <= limite_train]
test = dataset[dataset.fecha_corte >= inicio_test]

# 4. Entrenamiento y Evaluación
modelo = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000))
modelo.fit(train[FEATURES], train.y)
p_modelo = modelo.predict_proba(test[FEATURES])[:, 1]

tasa = train.groupby("vtm_id").y.mean()
p_ingenua = test.vtm_id.map(tasa).fillna(train.y.mean())

print("\n--- Resultados de Evaluación ---")
print("Prevalencia test:", round(test.y.mean(), 4))
print("PR-AUC Tasa ingenua:", round(average_precision_score(test.y, p_ingenua), 4))
print("PR-AUC Regresión Logística:", round(average_precision_score(test.y, p_modelo), 4))

test_eval = test.assign(p=p_modelo)
top100 = test_eval.sort_values("p", ascending=False).groupby("fecha_corte").head(100)
print("Precisión Top 100:", round(top100.y.mean(), 3))

print("\n--- Coeficientes ---")
print(pd.Series(modelo[-1].coef_[0], index=FEATURES).sort_values())

# 5. Reentrenamiento global y guardado
modelo.fit(dataset[FEATURES], dataset.y)

hoy = pd.Timestamp("2026-11-08")
actual = filas_corte(hoy)
actual["riesgo"] = modelo.predict_proba(actual[FEATURES])[:, 1]

p95, p80 = actual.riesgo.quantile([0.95, 0.80])
actual["nivel"] = np.select([actual.riesgo >= p95, actual.riesgo >= p80], ["alto", "medio"], "bajo")

salida = actual[["cn", "riesgo", "nivel"]].assign(
    horizonte_dias=HORIZONTE,
    modelo="regresion_logistica_v0",
    fecha_calculo=hoy.date()
)

salida.round({"riesgo": 4}).to_csv("data/cleaned/riesgo_linea_base.csv", sep=";", index=False)
joblib.dump(modelo, "models/regresion_logistica_v0.joblib")
print("\n¡Entrenamiento completado! Artefactos guardados con éxito.")