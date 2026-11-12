import glob
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------
# Configuración global y constantes
# ---------------------------------------------------------
HORIZONTE = 30
CORTES = pd.date_range("2026-05-04", "2026-10-05", freq="7D")
CONTEOS = ["n_alt_dcp", "n_alt_vtm", "n_labs_vtm", "inc_lab_90d", "inc_vtm_90d", "activas_vtm_t", "activas_dcp_t"]
BINARIAS = ["generico", "huerfano", "biosimilar", "receta", "ema", "envase_clinico", "no_sustituible"]
FEATURES = CONTEOS + BINARIAS + ["antiguedad_anios"]


def cargar_datos(ruta_inc="data/cleaned/incidencias.csv", ruta_pres="data/cleaned/presentaciones.csv"):
    """Carga los DataFrames mapeando automáticamente separadores y columnas clave."""
    if not os.path.exists(ruta_pres):
        candidatos = glob.glob("data/cleaned/medicamentos-limpios*.csv") + glob.glob("data/cleaned/presentaciones*.csv")
        if candidatos:
            ruta_pres = candidatos[0]
            print(f"Cargando presentaciones desde: {ruta_pres}")
        else:
            raise FileNotFoundError(
                "No se encontró ningún archivo de presentaciones en 'data/cleaned/'. "
                "Ejecuta primero 'python -m src.main' para generar los datos limpios."
            )

    inc = pd.read_csv(ruta_inc, sep=";", dtype={"cn": str, "nregistro": str}, parse_dates=["fecha_inicio", "fecha_fin"])

    with open(ruta_pres, 'r', encoding='utf-8') as f:
        primera_linea = f.readline()
    sep_pres = ";" if ";" in primera_linea else ","

    pres_todas = pd.read_csv(ruta_pres, sep=sep_pres, dtype={"cn": str, "nregistro": str})

    renombres = {
        "es_comercializado": "comercializado",
        "requiere_receta": "receta",
        "es_generico": "generico",
        "principio_activo_norm": "vtm_id",
        "forma_farmaceutica_norm": "dcp_id"
    }
    pres_todas = pres_todas.rename(columns=renombres)

    if "cn" not in pres_todas.columns and "nregistro" in pres_todas.columns:
        pres_todas["cn"] = pres_todas["nregistro"]
    if "nregistro" not in pres_todas.columns and "cn" in pres_todas.columns:
        pres_todas["nregistro"] = pres_todas["cn"]

    columnas_defecto = {
        "huerfano": False,
        "biosimilar": False,
        "ema": False,
        "envase_clinico": False,
        "nosustituible_id": 0,
        "vtm_id": pres_todas.get("principio_activo", "DESCONOCIDO"),
        "dcp_id": pres_todas.get("forma_farmaceutica", "DESCONOCIDO")
    }
    for col, val in columnas_defecto.items():
        if col not in pres_todas.columns:
            pres_todas[col] = val

    pres_todas["fecha_autorizacion"] = pd.to_datetime(pres_todas.get("fecha_autorizacion"), errors="coerce")
    if pres_todas["fecha_autorizacion"].dt.tz is not None:
        pres_todas["fecha_autorizacion"] = pres_todas["fecha_autorizacion"].dt.tz_convert("Europe/Madrid").dt.tz_localize(None)

    pres_todas["comercializado"] = pres_todas["comercializado"].fillna(True).astype(bool)

    return inc, pres_todas


def detectar_columna_link(pres: pd.DataFrame, inc: pd.DataFrame) -> str:
    """Determina automáticamente si la unión entre tablas debe hacerse por 'cn' o por 'nregistro'."""
    if "cn" in pres.columns and "cn" in inc.columns and pres["cn"].isin(inc["cn"]).any():
        return "cn"
    if "nregistro" in pres.columns and "nregistro" in inc.columns and pres["nregistro"].isin(inc["nregistro"]).any():
        return "nregistro"
    return "cn" if "cn" in pres.columns else "nregistro"


def calcular_features_estaticas(pres_todas: pd.DataFrame, col_link: str) -> pd.DataFrame:
    """Calcula métricas estáticas de competencia y sustitución sobre las presentaciones comercializadas."""
    pres = pres_todas[pres_todas["comercializado"]].copy()
    pres["dcp_id"] = pres["dcp_id"].astype("string").fillna("DESCONOCIDO")
    pres["vtm_id"] = pres["vtm_id"].astype("string").fillna("DESCONOCIDO")

    pres["n_alt_dcp"] = pres.groupby("dcp_id")[col_link].transform("count").fillna(0)
    pres["n_alt_vtm"] = (pres.groupby("vtm_id")[col_link].transform("count") - 1).fillna(0)
    pres["n_labs_vtm"] = pres.groupby("vtm_id")["laboratorio"].transform("nunique").fillna(1)
    pres["no_sustituible"] = (pres["nosustituible_id"] != 0).astype(int)
    return pres


def filas_corte(t: pd.Timestamp, pres: pd.DataFrame, pres_todas: pd.DataFrame, inc: pd.DataFrame, col_link: str, horizonte: int = HORIZONTE) -> pd.DataFrame:
    """Genera las observaciones y etiqueta objetivo para una fecha de corte específica."""
    col_inc = col_link if col_link in inc.columns else ("cn" if "cn" in inc.columns else "nregistro")

    activas = inc[(inc.fecha_inicio <= t) & (inc.fecha_fin.isna() | (inc.fecha_fin > t))]
    nuevas = inc[(inc.fecha_inicio > t) & (inc.fecha_inicio <= t + pd.Timedelta(days=horizonte))]
    previas = inc[(inc.fecha_inicio <= t) & (inc.fecha_inicio > t - pd.Timedelta(days=90))]

    df = pres[~pres[col_link].isin(activas[col_inc])].copy()
    df["fecha_corte"] = t
    df["y"] = df[col_link].isin(nuevas[col_inc]).astype(int)

    info = pres_todas[[col_link, "laboratorio", "vtm_id", "dcp_id"]].drop_duplicates(subset=[col_link])
    prev = previas.merge(info, left_on=col_inc, right_on=col_link, how="inner")
    act = activas.merge(info, left_on=col_inc, right_on=col_link, how="inner")

    df["inc_lab_90d"] = df.laboratorio.map(prev.laboratorio.value_counts()).fillna(0)
    df["inc_vtm_90d"] = df.vtm_id.map(prev.vtm_id.value_counts()).fillna(0)
    df["activas_vtm_t"] = df.vtm_id.map(act.vtm_id.value_counts()).fillna(0)
    df["activas_dcp_t"] = df.dcp_id.map(act.dcp_id.value_counts()).fillna(0)
    df["antiguedad_anios"] = (t - df.fecha_autorizacion).dt.days / 365.25

    for c in CONTEOS:
        df[c] = np.log1p(df[c].fillna(0))

    df[BINARIAS] = df[BINARIAS].fillna(False).astype(int)
    df["antiguedad_anios"] = df["antiguedad_anios"].fillna(df["antiguedad_anios"].median()).fillna(0)
    return df


def construir_dataset(pres: pd.DataFrame, pres_todas: pd.DataFrame, inc: pd.DataFrame, col_link: str, cortes=CORTES, horizonte: int = HORIZONTE) -> pd.DataFrame:
    """Construye y concatena la matriz de datos completa acumulando todas las fechas de corte."""
    return pd.concat([filas_corte(t, pres, pres_todas, inc, col_link, horizonte) for t in cortes], ignore_index=True)


def hacer_split_temporal(dataset: pd.DataFrame, cortes=CORTES, horizonte: int = HORIZONTE, semanas_test: int = 4):
    """Separa el dataset en train y test manteniendo una ventana de separación de 30 días."""
    inicio_test = cortes[-semanas_test]
    limite_train = inicio_test - pd.Timedelta(days=horizonte)

    train = dataset[dataset.fecha_corte <= limite_train]
    test = dataset[dataset.fecha_corte >= inicio_test]
    return train, test


def crear_pipeline_modelo():
    """Instancia el pipeline con imputador de nulos, escalado estándar y regresión logística balanceada."""
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=1000)
    )


def evaluar_modelo(modelo, train: pd.DataFrame, test: pd.DataFrame):
    """Entrena en train, compara contra la tasa ingenua por principio activo y computa la precisión top 100."""
    modelo.fit(train[FEATURES], train.y)
    p_modelo = modelo.predict_proba(test[FEATURES])[:, 1]

    tasa = train.groupby("vtm_id").y.mean()
    p_ingenua = test.vtm_id.map(tasa).fillna(train.y.mean())

    pr_auc_ingenua = average_precision_score(test.y, p_ingenua)
    pr_auc_modelo = average_precision_score(test.y, p_modelo)

    test_eval = test.assign(p=p_modelo)
    top100 = test_eval.sort_values("p", ascending=False).groupby("fecha_corte").head(100)
    precision_top100 = top100.y.mean()

    print("\n--- Resultados de Evaluación ---")
    print(f"Prevalencia test: {test.y.mean():.4f}")
    print(f"PR-AUC Tasa ingenua: {pr_auc_ingenua:.4f}")
    print(f"PR-AUC Regresión Logística: {pr_auc_modelo:.4f}")
    print(f"Precisión Top 100: {precision_top100:.3f}")

    try:
        nombres_features = modelo.named_steps["simpleimputer"].get_feature_names_out(FEATURES)
    except Exception:
        nombres_features = FEATURES

    print("\n--- Coeficientes ---")
    print(pd.Series(modelo[-1].coef_[0], index=nombres_features).sort_values())

    return {
        "pr_auc_ingenua": pr_auc_ingenua,
        "pr_auc_modelo": pr_auc_modelo,
        "precision_top100": precision_top100
    }


def exportar_artefactos(
    modelo,
    dataset: pd.DataFrame,
    pres: pd.DataFrame,
    pres_todas: pd.DataFrame,
    inc: pd.DataFrame,
    col_link: str,
    fecha_calculo: pd.Timestamp = pd.Timestamp("2026-11-08"),
    ruta_csv: str = "data/cleaned/riesgo_linea_base.csv",
    ruta_modelo: str = "models/regresion_logistica_v0.joblib"
):
    """Reentrena el modelo con el 100% de los datos y guarda el CSV de puntuaciones y el binario .joblib."""
    os.makedirs(os.path.dirname(ruta_csv), exist_ok=True)
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)

    modelo.fit(dataset[FEATURES], dataset.y)

    actual = filas_corte(fecha_calculo, pres, pres_todas, inc, col_link)
    actual["riesgo"] = modelo.predict_proba(actual[FEATURES])[:, 1]

    p95, p80 = actual.riesgo.quantile([0.95, 0.80])
    actual["nivel"] = np.select([actual.riesgo >= p95, actual.riesgo >= p80], ["alto", "medio"], "bajo")

    salida = actual[[col_link, "riesgo", "nivel"]].rename(columns={col_link: "cn"}).assign(
        horizonte_dias=HORIZONTE,
        modelo="regresion_logistica_v0",
        fecha_calculo=fecha_calculo.date()
    )

    salida.round({"riesgo": 4}).to_csv(ruta_csv, sep=";", index=False)
    joblib.dump(modelo, ruta_modelo)
    print(f"\n¡Artefactos guardados exitosamente en:\n - {ruta_csv}\n - {ruta_modelo}")


def ejecutar_pipeline_completo():
    """Orquesta la ejecución secuencial completa del baseline."""
    inc, pres_todas = cargar_datos()
    col_link = detectar_columna_link(pres_todas, inc)
    print(f"Columna de enlace identificada: '{col_link}'")

    pres = calcular_features_estaticas(pres_todas, col_link)
    dataset = construir_dataset(pres, pres_todas, inc, col_link)
    print(f"Dataset generado: {len(dataset)} filas | Prevalencia: {dataset.y.mean():.4f}")

    train, test = hacer_split_temporal(dataset)
    modelo = crear_pipeline_modelo()
    evaluar_modelo(modelo, train, test)
    exportar_artefactos(modelo, dataset, pres, pres_todas, inc, col_link)


if __name__ == "__main__":
    ejecutar_pipeline_completo()