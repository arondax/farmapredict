# Exploración de `/presentaciones` (snapshot del 05/11/2026)

Fichero: `raw/cima/presentaciones_20261105_173524.json` (rama `snapshots`, 58 MB).
Es el catálogo de **presentaciones**: una fila por **CN** (código nacional, la caja concreta que se vende). Es la tabla principal para la limpieza, el backend y el modelo.

El JSON está guardado en una sola línea (sin sangría, para que ocupe menos), por eso no se lee bien en un editor. Para ver un registro concreto:

```powershell
python -c "import json; d=json.load(open('../farmapredict-snapshots/raw/cima/presentaciones_20261105_173524.json', encoding='utf-8')); print(json.dumps(next(r for r in d if r['cn']=='917070'), ensure_ascii=False, indent=2))"
```

## Cifras

| Dato | Valor |
| --- | --- |
| Registros (CN) | 42.083, todos distintos |
| `nregistro` distintos (medicamentos) | 25.518 |
| Comercializadas (`comerc: true`) | 20.625 (49 %) |
| No comercializadas | 21.458 |
| Con problema de suministro activo (`psum: true`) | 917 (915 de ellas comercializadas) |
| DCP distintos | 7.055 |
| Sin DCP | 8 (ninguna comercializada) |
| Sin `vtm` (principio activo) | 1 |
| Genéricos | 23.291 |
| Revocadas (`estado.rev`) | 7.316 |
| Suspendidas (`estado.susp`) | 1.118 |
| `estado.aut` nulo | 8.434 (todas las revocadas y suspendidas) |

## Campos

| Campo | Presente en | Tipo | Notas para la limpieza |
| --- | --- | --- | --- |
| `cn` | 42.083 | texto, 6 dígitos | **Clave.** Mantener como texto |
| `nregistro` | 42.083 | texto | Une con `/medicamentos` (vías, forma farmacéutica). Sin ceros a la izquierda |
| `nombre` | 42.083 | texto | Nombre comercial + envase |
| `pactivos` | 42.083 | texto | Principios activos concatenados (en mayúsculas) |
| `labtitular` | 42.083 | texto | Laboratorio titular → columna `laboratorio` |
| `labcomercializador` | 42.083 | texto | **Siempre "N/A": descartar** |
| `cpresc` | 42.083 | texto | Condiciones de prescripción |
| `estado.aut` / `.rev` / `.susp` | 42.083 | epoch ms | Fechas a medianoche de Madrid en UTC: `tz_convert("Europe/Madrid")` antes de sacar el día. `aut` es nulo en revocadas y suspendidas |
| `comerc` | 42.083 | booleano | Comercializada hoy (no en cada fecha pasada) |
| `receta`, `generico`, `huerfano`, `biosimilar`, `ema`, `conduc`, `triangulo` | 42.083 | booleano | Candidatas a features |
| `psum` | 42.083 | booleano | **Problema de suministro activo hoy. No usar como feature (es la etiqueta: fuga de datos)** |
| `detalleProblemaSuministro` | 917 | objeto | Mismo dato que `/psuministro` (cn, fini, activo, observ). **Tampoco usar como feature** |
| `distribucionControlada` | 19 | booleano | Solo aparece cuando es `true` |
| `nosustituible` | 42.083 | objeto `{id, nombre}` | Si el medicamento no es sustituible por normativa (`id: 0` = sustituible). Útil para el recomendador |
| `envaseClinico` | 3.980 | booleano | Solo aparece cuando es `true` (envase hospitalario) |
| `vtm` | 42.082 | objeto `{id, nombre}` | Principio activo normalizado → `vtm_id`, `principio_activo` |
| `dcp` | 42.075 | objeto `{id, nombre}` | Principio activo + dosis + forma → `dcp_id`, `dcp_nombre`. **Clave de los sustitutos** |
| `dcpf` | 42.075 | objeto `{id, nombre}` | DCP + tamaño de envase |
| `principiosActivos` | 42.083 | lista | Con `cantidad` y `unidad` de cada principio activo |
| `excipientes` | 32.702 | lista | No se usa |
| `docs`, `fotos` | 42.083 / 10.427 | listas | Enlaces a ficha técnica, prospecto e imágenes. No se usan |
| `notas`, `materialesInf` | 42.083 | booleano | Si hay notas de seguridad o materiales informativos |

Los objetos (`vtm`, `dcp`, `estado`…) hay que aplanarlos con el patrón `(r.get("dcp") or {}).get("id")`, porque pueden faltar. Los `id` de DCP son números de hasta 15 cifras: guardarlos como texto.

## Ejemplo: Becloforte (CN 917070), con problema de suministro activo

```json
{
  "nregistro": "59377",
  "cn": "917070",
  "nombre": "BECLOFORTE 250 microgramos/inhalación SOLUCION PARA INHALACION EN ENVASE A PRESION , 1 cartucho de 200 dosis",
  "pactivos": "BECLOMETASONA DIPROPIONATO",
  "labtitular": "Glaxosmithkline S.A.",
  "labcomercializador": "N/A",
  "cpresc": "Medicamento Sujeto A Prescripción Médica. Tratamiento De Larga Duración",
  "estado": { "aut": 707349600000 },
  "comerc": true,
  "conduc": false,
  "receta": true,
  "generico": false,
  "triangulo": false,
  "huerfano": false,
  "biosimilar": false,
  "nosustituible": {
    "id": 4,
    "nombre": "Medicamentos para el aparato respiratorio administrados por vía inhalatoria"
  },
  "psum": true,
  "notas": true,
  "materialesInf": false,
  "ema": false,
  "docs": [
    { "tipo": 1, "url": "https://cima.aemps.es/cima/pdfs/ft/59377/FT_59377.pdf", "secc": false },
    { "tipo": 2, "url": "https://cima.aemps.es/cima/pdfs/p/59377/P_59377.pdf", "secc": false }
  ],
  "fotos": [
    { "tipo": "materialas", "url": "https://cima.aemps.es/cima/fotos/thumbnails/materialas/59377/59377_materialas.jpg", "fecha": 1759737314000 },
    { "tipo": "formafarmac", "url": "https://cima.aemps.es/cima/fotos/thumbnails/formafarmac/59377/59377_formafarmac.jpg", "fecha": 1759737316000 }
  ],
  "principiosActivos": [
    { "id": 463, "codigo": "463DE", "nombre": "BECLOMETASONA DIPROPIONATO", "cantidad": "250", "unidad": "µg", "orden": 1 }
  ],
  "excipientes": [
    { "id": 4661, "nombre": "GLICEROL (E 422)", "cantidad": "0,779", "unidad": "mg", "orden": 1 },
    { "id": 1845, "nombre": "ETANOL ANHIDRO", "cantidad": "8,929", "unidad": "mg", "orden": 2 }
  ],
  "vtm": { "id": 1389007, "nombre": "beclometasona" },
  "dcp": { "id": 770276003, "nombre": "Beclometasona 250 microgramos/dosis inhalación pulmonar" },
  "dcpf": { "id": 39471000140105, "nombre": "Beclometasona 250 microgramos/dosis inhalación pulmonar 200 dosis 1 inhalador" },
  "detalleProblemaSuministro": {
    "cn": "917070",
    "fini": 1793746800000,
    "activo": true,
    "observ": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración."
  }
}
```

`estado.aut = 707349600000` es el 01/06/1992 en hora de Madrid. `fini = 1793746800000` es el 04/11/2026 en Madrid (03/11 en UTC).

## Para el modelo

- **Población:** las 20.625 presentaciones comercializadas. Una presentación que no se vende no puede tener un problema de suministro.
- **Fuga de datos:** `psum`, `detalleProblemaSuministro` y `notas` describen el estado **actual**. Si se usan como features, el modelo "ve" la respuesta. La etiqueta sale de `data/cleaned/incidencias.csv`, nunca de estos campos.
- **Features útiles que salen de aquí:** número de presentaciones comercializadas con el mismo `dcp` y con el mismo `vtm` (alternativas disponibles), `generico`, `huerfano`, `biosimilar`, `receta`, `ema`, `envaseClinico`, `nosustituible.id`, antigüedad desde `estado.aut` y el laboratorio (`labtitular`, para el historial de incidencias por laboratorio).
- `comerc` es el estado de **hoy**: usarlo para filtrar fechas de corte pasadas es una pequeña fuga temporal que hay que mencionar en las limitaciones.
