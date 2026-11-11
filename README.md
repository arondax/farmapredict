# FarmaPredict

Predicción de desabastecimientos de medicamentos y recomendación de sustitutivos a partir de datos públicos de la AEMPS (CIMA).

> Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data (Planeta FP) · Módulo C088 · Semestre 2609
>
> **Estado:** Fase NF3 completada (Modelo de línea base entrenado y evaluado).

## Objetivo

Construir una plataforma que permita estimar el riesgo de desabastecimiento de un medicamento en los próximos 30 días y recomendar sustitutivos equivalentes, para que farmacias y distribuidores anticipen sus pedidos y eviten interrumpir tratamientos.

**Criterios de éxito**

1. El clasificador supera en PR-AUC a una línea base ingenua (tasa histórica de incidencias por código ATC / VTM). **[Superado en NF3]**
2. El recomendador propone al menos un sustitutivo para la mayoría de los medicamentos con problema de suministro.
3. Todo el sistema se levanta con un único `docker compose up`.

## Problema

La información sobre problemas de suministro de medicamentos es pública, pero está dispersa y es reactiva. Las farmacias pierden ventas y capacidad de previsión en sus pedidos, y los pacientes ven interrumpidos sus tratamientos cuando no encuentran su fármaco ni una alternativa equivalente.

## Alcance

**Dentro (MVP)**

- Ingesta programada (Airflow) desde la API REST de AEMPS CIMA a PostgreSQL, con snapshots diarios para construir histórico propio.
- Clasificador XGBoost del riesgo de desabastecimiento a 30 días, comparado con una línea base.
- Recomendador de sustitutivos por reglas (principio activo, dosis y forma farmacéutica).
- API REST en FastAPI (riesgo y sustitutivos).
- Dashboard en Streamlit: alertas y comparador de sustitutivos.
- Entorno reproducible con Docker Compose y tests básicos (PyTest).

**Dentro condicionado** (solo cuando el MVP funcione de extremo a extremo)

- Previsión de demanda estacional por ATC (Prophet) con datos del Ministerio de Sanidad.
- Ordenación de sustitutivos por similitud de fichas técnicas (embeddings + Qdrant).
- PySpark, solo si el volumen de datos lo justifica.
- Simulador de pedidos con datos sintéticos.

**Fuera**

- Integración con robots de almacenamiento, ERPs o receta electrónica.
- Aplicaciones móviles nativas.
- Diagnóstico médico o prescripción clínica.
- Datos reales de farmacias, autenticación y multiusuario.
- Despliegue en la nube.
- Reentrenamiento automático y monitorización de modelos.

Los sustitutivos que recomiende el sistema son **informativos**: la decisión final corresponde siempre al farmacéutico.

## Arquitectura

| Pieza | Diseño (Fase 1) | Implementado en NF3 |
|---|---|---|
| Ingesta | Airflow + Python | Python + **GitHub Actions con cron** (el plan B de la Fase 1). Snapshot diario de problemas de suministro en la rama `snapshots` |
| Almacenamiento | PostgreSQL | Ficheros (raw en la rama `snapshots`, limpio en `data/cleaned/`) servidos a través de `src/backend/datos.py`. PostgreSQL, en NF4 |
| Modelo de riesgo | XGBoost + regresión logística como baseline | Regresión logística + Imputación de nulos + Escalado estándar (Implementado). XGBoost, en NF4 |
| Recomendador | Reglas de equivalencia | Sustitutos por DCP + alternativas por principio activo y vía |
| API | FastAPI | En desarrollo (`/medicamentos/{cn}/riesgo` consume `riesgo_linea_base.csv`) |
| Dashboard | Streamlit | En desarrollo |
| Entorno | Docker Compose | Entorno virtual de Python. Docker Compose, en NF4 |

Prophet, Qdrant/embeddings y PySpark forman parte de la ampliación (ver Alcance). Entorno base: Python 3.11.

## Modelo de Línea Base (NF3)

Se ha implementado y entrenado el pipeline del modelo de regresión logística de línea base (`src.api.entrenar`), el cual estima la probabilidad/riesgo de que un medicamento comercializado empiece un problema de suministro en los próximos 30 días.

### Evaluación y Resultados (Out-of-Sample)

La evaluación se realizó mediante un **split temporal estricto** reservando las últimas 4 semanas de datos para el conjunto de test y dejando un margen de 30 días entre train y test para evitar la fuga de información (*data leakage*).

- **Dataset total:** 302.748 observaciones (23 fechas de corte semanales entre mayo y octubre de 2026).
- **Prevalencia global:** 0,0097 (0,97 %).
- **Prevalencia en test:** 0,0116 (1,16 %).
- **PR-AUC Tasa Ingenua (Baseline por VTM):** 0,0174
- **PR-AUC Regresión Logística (Modelo):** **0,0256** *(Supera a la tasa ingenua)*
- **Precisión Top 100 semanal:** 0,028 (2,8 % de acierto sobre las 100 presentaciones de mayor riesgo por semana).

### Coeficientes Clave
- **Empujan el riesgo al alza (Coeficientes Positivos):** Historial de incidencias del laboratorio (`inc_lab_90d`: +0.744), incidencias activas en el mismo VTM (`activas_vtm_t`: +0.444), requerimiento de receta (`receta`: +0.148) y antigüedad en años (`antiguedad_anios`: +0.128).
- **Reducen el riesgo (Coeficientes Negativos):** Número de alternativas por VTM comercializadas (`n_alt_vtm`: -0.556) y número de laboratorios competidores (`n_labs_vtm`: -0.112).

### Artefactos Generados
- `data/cleaned/riesgo_linea_base.csv`: Predicciones con el nivel de riesgo categorizado (`alto`, `medio`, `bajo`) por percentiles para consumo directo de la API.
- `models/regresion_logistica_v0.joblib`: Binario del pipeline completo entrenado (Imputer + Scaler + LogisticRegression).

### Limitaciones Técnicas Documentadas
1. **Puntuación de riesgo:** La salida `riesgo` es una puntuación relativa y no una probabilidad absoluta, debido al ajuste del parámetro `class_weight="balanced"` para compensar el desbalance de clases. Los niveles de riesgo se asignan mediante percentiles (p95 = alto, p80 = medio).
2. **Medicamentos con problema activo:** Se excluyen de las predicciones en la fecha de corte, ya que el modelo predice *nuevos* desabastecimientos. La API devuelve 404 "Sin predicción" para CNs con incidencia activa.
3. **Limitación del histórico:** El periodo de entrenamiento comienza en mayo de 2026 debido a la disponibilidad histórica de los snapshots en AEMPS CIMA.

## Datos

- **API REST de AEMPS CIMA:** medicamentos, códigos ATC, fichas técnicas y problemas de suministro. Públicos, sin datos personales.
- **Facturación de recetas del SNS (Ministerio de Sanidad):** datos públicos y agregados, como proxy de demanda. Granularidad por verificar.
- **Generador sintético (Faker + NumPy):** ventas por farmacia. Solo valida el pipeline, el dashboard y el volumen, no la capacidad predictiva.

**Etiqueta:** se considera desabastecimiento cuando existe un problema de suministro activo para el medicamento en los 30 días posteriores a la fecha de referencia (sujeto a lo que devuelva CIMA).

Los datasets **no se versionan** en el repositorio (`data/` está en `.gitignore`).

| Fichero en `snapshots` (`raw/cima/`) | Contenido |
|---|---|
| `psuministro_YYYYmmdd_HHMMSS.json` | Problemas de suministro activos de cada día (uno por día) |
| `backfill_psuministro_20261105.jsonl` | Último episodio de cada CN (consultado el 05/11/2026) |
| `presentaciones_20261105_173524.json` | Catálogo de presentaciones (CN de 6 dígitos) |
| `medicamentos-todos_20261019_181813.json` | Catálogo de medicamentos (nregistro) |

## Equipo

| Rol | Responsable | Apoyo en | Foco |
|---|---|---|---|
| Data | Alejandro Ronda  | ML | Ingesta, PostgreSQL, Airflow, EDA, recomendador |
| ML | Francisco Antonio Tortosa | Data | Variables, etiqueta, modelos y evaluación |
| Platform | Alejandro Ronda  | BI | API, Docker Compose, tests, gestión de PR |
| BI | Mohamed Ayman Oumghar Seghrouchni | Platform | Dashboard, KPIs, documentación |

## Organización del repositorio

```text
farmapredict/
├── .github/workflows/
│   └── snapshot_psuministro.yml   # snapshot diario de /psuministro (cron)
├── docs/                          # documentación, entregables y contrato de la API
├── models/                        # modelos entrenados (.joblib)
│   └── regresion_logistica_v0.joblib
├── src/
│   ├── config.py                  # rutas y configuración (.env)
│   ├── main.py                    # pipeline de presentaciones: raw → cleaned
│   ├── snapshot_diario.py         # descarga un endpoint paginado de CIMA (raw)
│   ├── backfill_psuministro.py    # backfill del último episodio por CN (ejecutado una vez)
│   ├── construir_incidencias.py   # genera data/cleaned/incidencias.csv
│   ├── api/                       # cliente de CIMA, transformaciones y entrenamiento
│   │   ├── api.py                 # cliente HTTP con reintentos y paginación
│   │   ├── esquemas_respuesta.py  # modelos Pydantic de las respuestas de CIMA
│   │   ├── almacenamiento.py      # guardado raw (JSON) y CSV
│   │   ├── transformaciones.py    # JSON de medicamentos → tabla plana
│   │   ├── limpieza_medicamentos.py
│   │   ├── incidencias.py         # une snapshots y backfill en episodios
│   │   └── entrenar.py            # pipeline de entrenamiento y evaluación ML (NF3)
│   └── backend/                   # lógica del producto
│       ├── datos.py               # acceso a datos (hoy ficheros; PostgreSQL en NF4)
│       └── servicios.py           # búsqueda, ficha y sustitutos
├── requirements.txt
├── .env.example
└── README.md
```
## Flujo de trabajo

- No se sube nada a `main` sin Pull Request aprobada por al menos otra persona del equipo.
- Todo trabajo tiene una issue asignada.
- Las decisiones se documentan (en la issue, en la PR o en `docs/`).
- Se respeta el reparto de roles, pero se ayuda cuando alguien está bloqueado.

## Cómo ejecutarlo

## Requisitos

- **Python 3.11** (obligatorio)

> ⚠️ No uséis Python 3.12+ por ahora: algunas dependencias (p. ej. `scikit-learn==1.6.1`)
> no tienen wheels precompilados para versiones más nuevas y pip intentará compilarlas,
> lo que falla en Windows sin compilador de C.

### Instalación

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version   # debe mostrar 3.11.x
python -m pip install -r requirements.txt
```

### 1. Clonar e instalar

```bash
git clone https://github.com/arondax/farmapredict.git
cd farmapredict
python -m venv .venv
.venv\Scripts\activate          # Windows (en Linux/macOS: source .venv/bin/activate)
python -m pip install -r requirements.txt
```

Usad `python -m pip` en lugar de `pip`. En Windows 11 con Smart App Control activo, `pip.exe` y algunas DLL de pandas pueden bloquearse ("Una directiva de Control de aplicaciones bloqueó este archivo"). Si ocurre, hay que desactivar Smart App Control o usar WSL2.

### 2. Datos

Abrir la rama `snapshots` como carpeta junto al repo (una sola vez):

```bash
git fetch origin snapshots
git worktree add ../farmapredict-snapshots snapshots
```

Configurar la ruta (una sola vez):

```bash
copy .env.example .env          # en Linux/macOS: cp .env.example .env
```

Para traer los snapshots nuevos del día:

```bash
git -C ../farmapredict-snapshots pull
```

### 3. Generar los datos limpios

```bash
python -m src.construir_incidencias   # → data/cleaned/incidencias.csv
python -m src.main                     # → data/cleaned/presentaciones.csv
```
### 4. Entrenar el modelo de línea base (ML)

```bash
python -m src.api.entrenar
```

### 5. API y front

En desarrollo (rama `feature/api`).
