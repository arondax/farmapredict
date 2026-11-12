# Limitaciones conocidas y deuda técnica (NF3)

Revisión del 12/11/2026 sobre la rama `feature/api`, ejecutando el flujo completo del README con Python 3.11 y los snapshots de la rama `snapshots` (catálogo de presentaciones del 05/11/2026; psuministro hasta el 12/11/2026).

Aquí se recoge lo que **no se corrige en NF3**: qué pasa, de dónde viene, cuánto afecta y cómo se arreglará. Las cifras se han obtenido ejecutando el código, no estimándolas.

| # | Limitación | Área | Gravedad | Previsto |
|---|---|---|---|---|
| 1 | La limpieza deja una sola presentación por medicamento | Datos | Alta | NF4 |
| 2 | 7 de las 15 features llegan constantes al modelo | Modelo | Media | NF4 |
| 3 | `dcp_id` del modelo es en realidad la forma farmacéutica | Modelo | Media | NF4 |
| 4 | Variables estáticas calculadas con el catálogo actual | Modelo | Media | NF4 |
| 5 | Histórico de incidencias corto y parcial | Datos | Media | Se reduce con el tiempo |
| 6 | La puntuación de riesgo no es una probabilidad | Modelo / front | Media | NF4 |
| 7 | La búsqueda con varias palabras exige texto contiguo | API | Baja | NF4 |
| 8 | Deuda técnica menor | Código | Baja | NF4 |

---

## 1. La limpieza deja una sola presentación por medicamento

**Qué pasa.** `src.main` genera `data/cleaned/presentaciones.csv` con **25.518 filas**, pero el snapshot de `/presentaciones` tiene **42.083 CN**. Se pierde el 39 % de las presentaciones.

**Causa.** `limpiar_medicamentos` deduplica por `CLAVE_SNAPSHOT = ["nregistro", "fecha_snapshot"]`. Esa clave era correcta cuando el pipeline procesaba `/medicamentos` (una fila por `nregistro`). Al pasar a `/presentaciones`, donde un mismo `nregistro` tiene varios CN (envases distintos), la deduplicación se queda con un CN por medicamento y descarta el resto.

**Impacto.**

- **Entrenamiento:** de los 1.859 CN con alguna incidencia, solo 1.312 están en el dataset. Las incidencias de los otros 547 no cuentan ni como etiqueta ni en las variables de historial (`inc_lab_90d`, `inc_vtm_90d`, `activas_vtm_t`).
- **API:** de los 19.696 CN comercializados y sin problema activo, **6.630 (34 %) no tienen predicción** y `/medicamentos/{cn}/riesgo` devuelve 404 "Sin predicción de riesgo para este CN". El dashboard lo explica como "por ejemplo, si ya tiene un problema de suministro activo", lo que no es cierto para estos CN.
- La búsqueda, la ficha y los sustitutos **no se ven afectados**: el backend lee el raw completo de presentaciones, no el CSV limpio.

**Solución prevista.** Deduplicar por `["cn", "fecha_snapshot"]` cuando la entrada sea `/presentaciones`. Prueba hecha con ese cambio:

| | Actual (por `nregistro`) | Con la corrección (por `cn`) |
|---|---|---|
| Presentaciones limpias | 25.518 | 42.083 |
| Observaciones del dataset | 302.748 | 455.432 |
| Prevalencia en test | 0,0116 | 0,0106 |
| PR-AUC tasa ingenua | 0,0174 | 0,0207 |
| PR-AUC regresión logística | 0,0256 | 0,0254 |
| Precisión Top 100 | 0,028 | 0,033 |

El modelo **sigue superando a la línea base** con la corrección, aunque con menos margen: la tasa ingenua mejora más que el modelo al tener más datos. Las cifras del README se actualizarán al reentrenar.

## 2. 7 de las 15 features llegan constantes al modelo

**Qué pasa.** Al entrenar, estas variables tienen coeficiente 0 porque valen lo mismo en todas las filas: `n_alt_dcp`, `activas_dcp_t`, `huerfano`, `biosimilar`, `ema`, `envase_clinico` y `no_sustituible`. El modelo usa en la práctica **8 variables**: `inc_lab_90d`, `inc_vtm_90d`, `activas_vtm_t`, `n_alt_vtm`, `n_labs_vtm`, `receta`, `generico` y `antiguedad_anios`.

**Causa.**

- `extraer_medicamentos` (`src/api/transformaciones.py`) se escribió para `/medicamentos` y lee `formaFarmaceuticaSimplificada` y `viasAdministracion`, que **no existen en `/presentaciones`**. En `presentaciones.csv`, `forma_farmaceutica` y `via_administracion` están vacías al 100 %, así que `dcp_id` vale "DESCONOCIDO" en todas las filas (ver punto 3).
- `huerfano`, `biosimilar`, `ema`, `envaseClinico` y `nosustituible` sí vienen en el JSON de presentaciones, pero no se extraen. `entrenar.cargar_datos` rellena las columnas que faltan con valores por defecto (`False` / `0`) sin avisar.

**Impacto.** El modelo no aprovecha información disponible y la lista de `FEATURES` sobrestima lo que realmente usa. Los resultados del README son correctos para las 8 variables efectivas.

**Solución prevista.** Extraer de `/presentaciones` los campos `dcp.id`, `huerfano`, `biosimilar`, `ema`, `envaseClinico` y `nosustituible.id`; obtener las vías cruzando con `/medicamentos` por `nregistro`. Sustituir los valores por defecto silenciosos de `cargar_datos` por un error si falta una columna esperada.

## 3. `dcp_id` del modelo es en realidad la forma farmacéutica

**Qué pasa.** `entrenar.cargar_datos` renombra `forma_farmaceutica_norm` a `dcp_id` (y `principio_activo_norm` a `vtm_id`).

**Causa.** Un DCP (principio activo + dosis + forma) no es una forma farmacéutica. Aunque la columna tuviera datos, `n_alt_dcp` contaría todas las presentaciones con la misma forma (por ejemplo, todos los comprimidos), no los equivalentes reales.

**Impacto.** Hoy ninguno, porque la columna está vacía (punto 2). Al corregir la extracción, el error se haría efectivo si no se cambia también este renombrado.

**Solución prevista.** Usar `dcp.id` y `vtm.id` del JSON de presentaciones, igual que el backend (`src/backend/datos.py`), y eliminar el renombrado.

## 4. Variables estáticas calculadas con el catálogo actual

**Qué pasa.** `n_alt_dcp`, `n_alt_vtm`, `n_labs_vtm` y el filtro de presentaciones comercializadas se calculan con el catálogo del 05/11/2026 y se aplican igual a todos los cortes, desde mayo.

**Impacto.** Hay cierta fuga de información del futuro: un medicamento retirado del mercado entre mayo y noviembre no aparece en los cortes antiguos, y el número de alternativas de mayo puede no coincidir con el de hoy. El split temporal evita la fuga en la etiqueta, pero no en estas variables.

**Solución prevista.** Con PostgreSQL y snapshots diarios del catálogo (NF4), calcular estas variables con el catálogo vigente en cada fecha de corte. Hasta tener ese histórico es una limitación inevitable.

## 5. Histórico de incidencias corto y parcial

**Qué pasa.** Los snapshots diarios de `/psuministro` empiezan el 04/11/2026. Lo anterior viene del backfill del 05/11, que solo devuelve el **último episodio de cada CN** (`/psuministro/v2/cn/{cn}`).

**Impacto.** Si un CN tuvo varios problemas de suministro entre mayo y octubre, solo se conoce el último. Las etiquetas positivas de los cortes antiguos están infrarrepresentadas, y las variables de historial (`inc_lab_90d`, `inc_vtm_90d`) también. Ya documentado en `docs/exploracion_psuministro.md`.

**Solución prevista.** Se reduce sola con el tiempo gracias al snapshot diario (GitHub Actions). Para NF4, entrenar solo con cortes cubiertos por snapshots cuando haya histórico suficiente, o ponderar los cortes antiguos.

## 6. La puntuación de riesgo no es una probabilidad

**Qué pasa.** El modelo se entrena con `class_weight="balanced"`, así que `riesgo` es una puntuación relativa, no una probabilidad. Con una prevalencia real del 1 %, las puntuaciones llegan a 0,947 (p95 = 0,79).

**Impacto.** El dashboard la muestra como porcentaje bajo el título "Riesgo a 30 días" (por ejemplo, "58,2 %"), lo que se puede leer como una probabilidad real. El nivel (`alto` / `medio` / `bajo`, por percentiles) sí es interpretable.

**Solución prevista.** En el dashboard, mostrar el nivel como dato principal y la puntuación como "puntuación relativa", no como porcentaje. Para tener probabilidades reales, calibrar el modelo (`CalibratedClassifierCV`) o entrenar sin `class_weight` y comparar.

## 7. La búsqueda con varias palabras exige texto contiguo

**Qué pasa.** `servicios.buscar` comprueba si el texto completo aparece tal cual en el nombre. "ibuprofeno" encuentra resultados, pero "ibuprofeno 600" no, porque en los nombres hay texto entre ambas palabras (por ejemplo, "IBUPROFENO CINFA 600 MG").

**Solución prevista.** Partir la consulta en palabras y exigir que aparezcan todas, en cualquier orden.

## 8. Deuda técnica menor

- **`src/frontend/app.py`:** usa `use_container_width`, obsoleto en Streamlit (avisa en cada ejecución; hay que pasar a `width="stretch"`). Además, `m["nombre"][:90]` falla si el nombre viene nulo, y el esquema `ResultadoBusqueda` lo permite.
- **`src/backend/servicios.py`:** `CRITERIO_SUSTITUTOS` está definido dos veces; la primera definición no se usa.
- **`src/api/entrenar.py`:** las rutas son relativas (`data/cleaned/...`) en lugar de usar `DATA_CLEANED_DIR` de `src/config.py`, así que solo funciona lanzado desde la raíz del repo. La `fecha_calculo` está fija (08/11/2026) y no avanza con los snapshots nuevos.
- **`.vscode/settings.json`:** configuración personal del editor versionada; añadir `.vscode/` a `.gitignore`.
