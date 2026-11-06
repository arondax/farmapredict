# Exploración de `/psuministro` (04/11/2026)

Prueba realizada para responder a una pregunta de diseño: **¿el endpoint `/psuministro` de CIMA devuelve histórico de problemas de suministro o solo los activos?** De la respuesta dependía cómo construir la etiqueta del modelo.

Script utilizado: `src/exploracion_psuministro.py` (eliminado tras la prueba; disponible en el historial de git).

## Salida

```text
psuministro | página 1: 200/920
psuministro | página 2: 400/920
psuministro | página 3: 600/920
psuministro | página 4: 800/920
psuministro | página 5: 920/920
Guardado en: data/raw/cima/psuministro_20261104_171429.json

Total registros: 920
Campos (frecuencia): {'cn': 920, 'nombre': 920, 'tipoProblemaSuministro': 920, 'fini': 920, 'activo': 920, 'observ': 920, 'ffin': 651}
activo: {True: 920}
fini: de 2016-05-05 a 2026-11-03
Incidencias por año de inicio: {2016: 3, 2019: 2, 2020: 3, 2021: 4, 2022: 6, 2023: 27, 2024: 41, 2025: 143, 2026: 691}
ffin pasada (cerradas): 0 | ffin futura: 651 | sin ffin: 269
CN únicos: 920 | CN con >1 incidencia: 0

Ejemplo:
{
  "cn": "917070",
  "nombre": "BECLOFORTE 250 microgramos/inhalación SOLUCION PARA INHALACION EN ENVASE A PRESION , 1 cartucho de 200 dosis",
  "tipoProblemaSuministro": 5,
  "fini": 1793746800000,
  "activo": true,
  "observ": "Existe/n otro/s medicamento/s con el mismo principio activo y para la misma vía de administración."
}
```

## Conclusiones

1. **El endpoint no tiene histórico:** los 920 registros tienen `activo: true` y ninguno tiene `ffin` pasada. Es una foto del estado actual.
2. **Un solo episodio por CN:** si un medicamento tuvo varios problemas, solo se ve el actual.
3. **`ffin` es la fecha de fin prevista**, no la real: las 651 que la traen son futuras y 269 no tienen fecha estimada.
4. **La distribución por año de inicio es un sesgo de supervivencia,** no una tendencia: solo quedan las incidencias antiguas que siguen activas (crónicas). No debe usarse como "evolución de los desabastecimientos".
5. **Las fechas son epoch en milisegundos, a medianoche de Madrid guardada en UTC:** `1793746800000` es el 04/11 en Madrid (03/11 en UTC). Por eso el script muestra `fini` hasta el 2026-11-03.

## Decisiones que provocó

- **Snapshots diarios** de `/psuministro` (GitHub Actions, rama `snapshots`) para construir histórico propio desde el 04/11.
- Búsqueda de otra fuente de histórico, que llevó a descubrir que `/psuministro/v2/cn/{cn}` sí conserva el último episodio resuelto, y de ahí el **backfill** del 05/11 (ver la bitácora).