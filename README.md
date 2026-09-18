# FarmaPredict

Predicción de desabastecimientos de medicamentos y recomendación de sustitutivos a partir de datos públicos de la AEMPS (CIMA).

> Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data (Planeta FP) · Módulo C088 · Semestre 2609
>
> **Estado:** fase NF1 (presentación y viabilidad). Aún no hay código; el stack y el alcance son provisionales y se irán refinando.

## Objetivo

Construir una plataforma que permita anticipar el riesgo de desabastecimiento de medicamentos y recomendar sustitutivos equivalentes, para ayudar a farmacias y distribuidores a proteger la continuidad de los tratamientos.

<!-- TODO: añadir métricas objetivo con línea base (p. ej. PR-AUC del clasificador frente a un modelo ingenuo; precisión de los sustitutivos frente a las equivalencias oficiales). -->

## Problema

La información sobre problemas de suministro de medicamentos es pública, pero está dispersa. Las farmacias pierden ventas y capacidad de previsión en sus pedidos, y los pacientes ven interrumpidos sus tratamientos cuando no encuentran su fármaco ni una alternativa equivalente.

## Alcance

| Dentro (IN) | Fuera (OUT) |
|---|---|
| Ingesta programada desde la API REST de AEMPS CIMA | Integración con robots de almacenamiento de farmacias |
| Modelo de clasificación del riesgo de desabastecimiento (30 días) | Escritura sobre ERPs o sistemas de receta electrónica |
| Previsión de demanda estacional por código ATC | Aplicaciones móviles nativas |
| Recomendador de sustitutivos por principio activo y forma | Diagnóstico médico o prescripción clínica |
| API REST y dashboard interactivo, todo en Docker Compose | Datos reales de farmacias, autenticación y multiusuario |

<!-- TODO: cerrar en equipo qué parte es MVP y qué parte queda como ampliación. -->

Los sustitutivos que recomiende el sistema son **informativos**: la decisión final corresponde siempre al farmacéutico.

## Arquitectura (alto nivel, provisional)

| Capa | Componentes previstos | Función |
|---|---|---|
| Ingesta y ETL | Apache Airflow, Python, PySpark | Consumir CIMA y transformar el catálogo |
| Almacenamiento | PostgreSQL, Qdrant | Datos relacionales y búsqueda vectorial |
| IA / ML | XGBoost, Prophet, embeddings | Riesgo de rotura, demanda y similitud de fármacos |
| API | FastAPI | Exponer predicciones y recomendaciones |
| Presentación | Streamlit, Plotly | Dashboard de alertas y comparador de sustitutivos |

Entorno base: Python 3.11 y Docker Compose.

## Datos

- **Fuente principal:** API REST de AEMPS CIMA (medicamentos, códigos ATC y problemas de suministro). Datos públicos y sin datos personales.
- **Datos sintéticos:** generador propio en Python para simular ventas por farmacia.
- **Alternativas en estudio:** snapshots locales de CIMA como plan B y fuentes públicas de consumo farmacéutico.

<!-- TODO: documentar condiciones de reutilización y límites de la API de CIMA. -->

Los datasets **no se versionan** en el repositorio (`data/` está en `.gitignore`).

## Equipo

| Rol | Responsable | Apoyo |
|---|---|---|
| Data Engineer | Alejandro Ronda | Francisco Antonio Tortosa |
| ML Engineer | Alejandro Ronda | Francisco Antonio Tortosa |
| Backend y MLOps | Alejandro Ronda | Francisco Antonio Tortosa |
| BI y DataViz | Alejandro Ronda | Francisco Antonio Tortosa |

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