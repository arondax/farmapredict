# FarmaPredict

Predicción de desabastecimientos de medicamentos y recomendación de sustitutivos a partir de datos públicos de la AEMPS (CIMA).

> Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data (Planeta FP) · Módulo C088 · Semestre 2609
>
> **Estado:** fase NF1 (presentación y viabilidad). Aún no hay código; el stack y el alcance son provisionales y se irán refinando.

## Objetivo

Construir una plataforma que permita estimar el riesgo de desabastecimiento de un medicamento en los próximos 30 días y recomendar sustitutivos equivalentes, para que farmacias y distribuidores anticipen sus pedidos y eviten interrumpir tratamientos.

**Criterios de éxito**

1. El clasificador supera en PR-AUC a una línea base ingenua (tasa histórica de incidencias por código ATC).
2. El recomendador propone al menos un sustitutivo para la mayoría de los medicamentos con problema de suministro.
3. Todo el sistema se levanta con un único `docker compose up`.

<!-- Los umbrales numéricos se fijarán tras medir la línea base (semana 2). -->

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

## Arquitectura (alto nivel, provisional)

| Pieza | Función | Tecnología |
|---|---|---|
| Ingesta y ETL | Descarga programada de CIMA, limpieza y carga | Apache Airflow, Python |
| Almacenamiento | Catálogo, histórico de suministro y variables del modelo | PostgreSQL |
| Modelo de riesgo | Clasificador a 30 días y modelos de referencia | XGBoost, regresión logística |
| Recomendador | Sustitutivos equivalentes por reglas | SQL / Python |
| API | Expone riesgo y sustitutivos | FastAPI |
| Dashboard | Semáforo de riesgo y comparador de sustitutivos | Streamlit, Plotly |
| Entorno | Despliegue reproducible | Docker Compose |

Prophet, Qdrant/embeddings y PySpark forman parte de la ampliación (ver Alcance). Entorno base: Python 3.11.

## Datos

- **API REST de AEMPS CIMA:** medicamentos, códigos ATC, fichas técnicas y problemas de suministro. Públicos, sin datos personales.
- **Facturación de recetas del SNS (Ministerio de Sanidad):** datos públicos y agregados, como proxy de demanda. Granularidad por verificar.
- **Generador sintético (Faker + NumPy):** ventas por farmacia. Solo valida el pipeline, el dashboard y el volumen, no la capacidad predictiva.

**Etiqueta:** se considera desabastecimiento cuando existe un problema de suministro activo para el medicamento en los 30 días posteriores a la fecha de referencia (sujeto a lo que devuelva CIMA).

<!-- TODO: documentar condiciones de reutilización y límites de la API de CIMA y del Ministerio (semana 1). -->

Los datasets **no se versionan** en el repositorio (`data/` está en `.gitignore`).

## Equipo

| Rol | Responsable | Apoyo en | Foco |
|---|---|---|---|
| Data | Alejandro Ronda  | ML | Ingesta, PostgreSQL, Airflow, EDA, recomendador |
| ML | Francisco Antonio Tortosa | Data | Variables, etiqueta, modelos y evaluación |
| Platform | Alejandro Ronda  | BI | API, Docker Compose, tests, gestión de PR |
| BI | Francisco Antonio Tortosa | Platform | Dashboard, KPIs, documentación |

## Organización del repositorio

```text
farmapredict/
├── docs/          # Documentación y entregables (NF1_Presentacion_y_Viabilidad.pdf)
├── src/           # Código fuente
├── data/          # Datos locales (vacío en el repo, solo .gitkeep)
├── environment/   # Configuración del entorno (Docker Compose, dependencias)
├── README.md
└── .gitignore
```

## Flujo de trabajo

- No se sube nada a `main` sin Pull Request aprobada por al menos otra persona del equipo.
- Todo trabajo tiene una issue asignada.
- Las decisiones se documentan (en la issue, en la PR o en `docs/`).
- Se respeta el reparto de roles, pero se ayuda cuando alguien está bloqueado.

## Cómo ejecutarlo

Pendiente: se completará cuando exista la primera versión del entorno.