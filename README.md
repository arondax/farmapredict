# FarmaPredict

Predicción de desabastecimientos de medicamentos y recomendación de sustitutivos a partir de datos públicos de la AEMPS (CIMA).

> Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data (Planeta FP) · Módulo C088 · Semestre 2609
>
> **Estado:** Fase NF3 completada: producto funcional en local (ingesta, modelo de línea base, API REST y dashboard).

## Objetivo

Construir una plataforma que permita estimar el riesgo de desabastecimiento de un medicamento en los próximos 30 días y recomendar sustitutivos equivalentes, para que farmacias y distribuidores anticipen sus pedidos y eviten interrumpir tratamientos.

**Criterios de éxito**

1. El clasificador supera en PR-AUC a una línea base ingenua (tasa histórica de incidencias por código ATC / VTM). **[Cumplido en NF3]**
2. El recomendador propone al menos un sustitutivo para la mayoría de los medicamentos con problema de suministro. **[Cumplido en NF3]**: de los 930 CN con problema activo (snapshot del 12/11/2026), el 77 % tiene al menos un sustituto equivalente (mismo DCP) y el 90 % tiene al menos un sustituto o una alternativa.
3. Todo el sistema se levanta con un único `docker compose up`. **[Previsto para NF4]**

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
| Modelo de riesgo | XGBoost + regresión logística como baseline | Regresión logística (imputación de nulos + escalado estándar). XGBoost, en NF4 |
| Recomendador | Reglas de equivalencia | Sustitutos por DCP + alternativas por principio activo y vía de administración |
| API | FastAPI | FastAPI: salud, búsqueda, ficha, sustitutos y riesgo (`src/backend/`) |
| Dashboard | Streamlit | Streamlit: búsqueda, ficha, sustitutos y riesgo, consumiendo la API (`src/frontend/app.py`) |
| Tests | PyTest | Tests de la API con datos de ejemplo (`tests/test_api.py`) |
| Entorno | Docker Compose | Entorno virtual de Python. Docker Compose, en NF4 |

Prophet, Qdrant/embeddings y PySpark forman parte de la ampliación (ver Alcance). Entorno base: Python 3.11.

## Modelo de línea base (NF3)

Se ha implementado y entrenado el pipeline del modelo de regresión logística de línea base (`src.api.entrenar`). El modelo estima el riesgo de que un medicamento comercializado empiece un problema de suministro en los próximos 30 días.

### Evaluación y resultados (out-of-sample)

La evaluación se hizo con un **split temporal estricto**: las últimas 4 semanas de datos se reservan para test y se deja un margen de 30 días entre train y test para evitar la fuga de información (*data leakage*).

- **Dataset total:** 302.748 observaciones (23 fechas de corte semanales entre mayo y octubre de 2026).
- **Prevalencia global:** 0,0097 (0,97 %).
- **Prevalencia en test:** 0,0116 (1,16 %).
- **PR-AUC tasa ingenua (baseline por VTM):** 0,0174
- **PR-AUC regresión logística (modelo):** **0,0256** *(supera a la tasa ingenua)*
- **Precisión Top 100 semanal:** 0,028 (2,8 % de acierto sobre las 100 presentaciones de mayor riesgo por semana).

Estas cifras se reproducen ejecutando los pasos 3 y 4 de "Cómo ejecutarlo" con los snapshots de la rama `snapshots`.

### Coeficientes clave

- **Empujan el riesgo al alza (coeficientes positivos):** historial de incidencias del laboratorio (`inc_lab_90d`: +0,744), incidencias activas en el mismo VTM (`activas_vtm_t`: +0,444), requerimiento de receta (`receta`: +0,148) y antigüedad en años (`antiguedad_anios`: +0,128).
- **Reducen el riesgo (coeficientes negativos):** número de alternativas por VTM comercializadas (`n_alt_vtm`: -0,556) y número de laboratorios competidores (`n_labs_vtm`: -0,112).

De las 15 variables definidas en `FEATURES`, **8 aportan información**. Las otras 7 llegan constantes al modelo (coeficiente 0) por cómo se generan hoy los datos limpios. Ver [docs/limitaciones_nf3.md](docs/limitaciones_nf3.md).

### Artefactos generados

- `data/cleaned/riesgo_linea_base.csv`: predicciones con el nivel de riesgo (`alto`, `medio`, `bajo`) asignado por percentiles, para consumo directo de la API.
- `models/regresion_logistica_v0.joblib`: binario del pipeline completo entrenado (Imputer + Scaler + LogisticRegression).

## Limitaciones conocidas

Resumen. El detalle (causa, cifras, impacto y solución prevista) está en [docs/limitaciones_nf3.md](docs/limitaciones_nf3.md).

1. **La puntuación de riesgo no es una probabilidad.** El modelo se entrena con `class_weight="balanced"` para compensar el desbalance de clases, así que `riesgo` es una puntuación relativa para ordenar medicamentos. Los niveles se asignan por percentiles (p95 = alto, p80 = medio).
2. **Medicamentos con problema activo.** Se excluyen de las predicciones en la fecha de corte, porque el modelo predice *nuevos* desabastecimientos. La API devuelve 404 "Sin predicción" para esos CN.
3. **La limpieza deja una presentación por medicamento.** `src.main` deduplica por `nregistro` y conserva 25.518 de los 42.083 CN. Por eso unos 6.600 CN comercializados y sin problema activo no tienen predicción de riesgo (la API devuelve 404).
4. **7 de las 15 features son constantes.** La extracción de `/presentaciones` no incluye forma farmacéutica, vías, DCP ni los indicadores de huérfano, biosimilar, EMA, envase clínico y no sustituible.
5. **Histórico corto y parcial.** El entrenamiento empieza en mayo de 2026. Antes de los snapshots diarios (desde el 04/11/2026) solo se conoce el último episodio de cada CN (backfill del 05/11), así que los CN con varios episodios están infrarrepresentados en los cortes antiguos.
6. **Variables estáticas calculadas sobre el catálogo actual.** Las alternativas por VTM, los laboratorios y el filtro de comercializados usan el catálogo de noviembre en todos los cortes, lo que introduce cierta información del futuro en los cortes antiguos.

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
├── docs/                          # documentación, entregables, contrato de la API y limitaciones
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
│   │   ├── transformaciones.py    # JSON de CIMA → tabla plana
│   │   ├── limpieza_medicamentos.py
│   │   ├── incidencias.py         # une snapshots y backfill en episodios
│   │   └── entrenar.py            # entrenamiento y evaluación del modelo (NF3)
│   ├── backend/                   # API REST (FastAPI)
│   │   ├── main.py                # punto de entrada: carga los datos al arrancar
│   │   ├── rutas.py               # endpoints HTTP (sin lógica de negocio)
│   │   ├── esquemas.py            # modelos de respuesta (contrato de la API)
│   │   ├── servicios.py           # búsqueda, ficha, sustitutos y riesgo
│   │   └── datos.py               # acceso a datos (hoy ficheros; PostgreSQL en NF4)
│   └── frontend/
│       └── app.py                 # dashboard Streamlit (consume la API)
├── tests/
│   └── test_api.py                # tests de la API con datos de ejemplo
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

Todos los comandos se lanzan desde la raíz del repositorio y con el entorno virtual activado.

### Requisitos

- **Python 3.11** (obligatorio). Las versiones de `requirements.txt` están probadas con 3.11; con versiones más nuevas, pip puede intentar compilar dependencias sin wheel precompilado, y eso falla en Windows sin compilador de C.
- Git.

### 1. Clonar e instalar

Windows (PowerShell):

```powershell
git clone https://github.com/arondax/farmapredict.git
cd farmapredict
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version   # debe mostrar 3.11.x
python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
git clone https://github.com/arondax/farmapredict.git
cd farmapredict
python3.11 -m venv .venv
source .venv/bin/activate
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

### 4. Entrenar el modelo de línea base

```bash
python -m src.api.entrenar             # → data/cleaned/riesgo_linea_base.csv y models/regresion_logistica_v0.joblib
```

Muestra por pantalla las métricas de evaluación y los coeficientes, y genera el fichero de riesgo que consume la API. Sin este paso la API funciona, pero `/medicamentos/{cn}/riesgo` devuelve 503 (modelo no disponible).

### 5. Arrancar la API

```bash
python -m uvicorn src.backend.main:app --reload
```

- API en `http://127.0.0.1:8000`.
- Documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs`.
- Al arrancar carga los snapshots más recientes de `FARMAPREDICT_RAW_DIR`; si falta alguno, indica qué comando ejecutar.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado, fecha de los datos cargados y si el modelo está disponible |
| GET | `/medicamentos?q=texto&limite=20` | Búsqueda por nombre (mínimo 3 caracteres, sin distinguir tildes ni mayúsculas) |
| GET | `/medicamentos/{cn}` | Ficha de la presentación y su problema de suministro activo, si lo hay |
| GET | `/medicamentos/{cn}/sustitutos` | Sustitutos equivalentes (mismo DCP) y alternativas (mismo principio activo y vía) |
| GET | `/medicamentos/{cn}/riesgo` | Puntuación y nivel de riesgo a 30 días |

Ejemplos de respuesta en [docs/ejemplos_endpoints.txt](docs/ejemplos_endpoints.txt).

### 6. Arrancar el dashboard

Con la API ya arrancada, en **otra terminal** (con el entorno virtual activado):

```bash
python -m streamlit run src/frontend/app.py
```

Se abre en `http://localhost:8501`. Por defecto llama a la API en `http://127.0.0.1:8000`; para cambiarlo, definid la variable de entorno `API_URL` antes de arrancar (PowerShell: `$env:API_URL = "http://..."`; Linux/macOS: `export API_URL=http://...`).

### 7. Tests

```bash
python -m pytest
```

Los tests usan datos de ejemplo en memoria: no necesitan los snapshots ni el modelo entrenado.