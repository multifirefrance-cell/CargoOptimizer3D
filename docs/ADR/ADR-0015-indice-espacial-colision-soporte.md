# ADR-0015: Índice espacial (`SpatialIndex`) para colisión, soporte y apilamiento

## Estado

Aceptada — retroactiva. La estructura de datos que describe este ADR
ya está implementada y en uso en producción desde el commit `8396576`
("Speed up packing engine 1.7x-3x via spatial index, candidate/pruning
caches, and simplified stacking"), y ha sido corregida y ampliada desde
entonces (fase OPT-16, `CLAUDE.md`). Este documento se escribe ahora,
como parte de la auditoría técnica previa a la Beta, para cerrar un
hueco de proceso: `docs/ProductBacklog.md` (ítem OPT-11) exige
explícitamente "un ADR explícito... cuando se retome, no antes" como
criterio de aceptación, y ese ADR nunca se redactó pese a que el código
ya existía. No cambia ni reabre ninguna decisión técnica — documenta,
con la evidencia real disponible hoy (tests de equivalencia, medición
en el caso de 2000 unidades), la decisión que de hecho ya se tomó e
implementó.

## Contexto

`docs/OptimizerPerformance.md`, sección "OPT-03 → OPT-11 (2026-07-17):
confirmación con un caso real, investigación cerrada sin código",
perfiló con `cProfile` el cuello de botella real del motor:
`geometry/collision.py::boxes_overlap` y
`rules/stacking_rules.py::find_direct_supporting_placements`
recorrían, sin ninguna estructura espacial, **todos** los
`existing_placements` por cada candidato evaluado — un costo que crece
de forma no lineal según se acumulan cajas colocadas (566.588 s de
tiempo propio en `boxes_overlap` para solo 300 instancias en el
escenario medido).

Esa sección cerró la investigación explícitamente **sin escribir
código todavía** y señaló dos riesgos que justificaban esa cautela:

1. Tocar `rules`/`geometry`, las capas más protegidas del proyecto.
2. El riesgo de que una implementación incorrecta introdujera un falso
   negativo de colisión o de soporte — silencioso y grave — y en
   particular que `stacking_rules.evaluate_supported_weight` (vigente
   en ese momento) necesitaba conocer, para cada soporte transitivo,
   todo lo que descansaba sobre él en **cualquier** parte del layout,
   no solo lo cercano.

Poco después (mismo periodo de trabajo, commit `8396576`) se decidió
proceder con la implementación, en vez de esperar a una fase separada
posterior — la razón práctica fue que la Beta 1.0 (empaquetado Windows,
ADR-0013) ya estaba cerrada y la siguiente prioridad real observada
(casos de usuario con miles de bultos) dependía directamente de
resolver esto. La condición 2 dejó de aplicar poco después por una
razón independiente: una fase posterior (documentada en `CLAUDE.md`,
"Fase OPT-13" citada desde el bloque de invariantes de `rules`)
eliminó por completo `evaluate_supported_weight` (peso soportado
acumulado/propagado) y el apilamiento recursivo del motor, precisamente
porque esa función era la única que de verdad necesitaba conocer el
layout completo en vez de solo el entorno cercano de cada candidato.
Con esa función fuera del sistema, un índice espacial que solo
devuelve vecinos cercanos deja de arriesgar ese caso concreto.

## Decisión

Se implementa `geometry/spatial_index.py::SpatialIndex`: una rejilla
de hash espacial (celdas de tamaño fijo) que indexa cada `Placement`
aceptado por las celdas que ocupa su caja, y expone `query_box(box)`
para devolver únicamente los `sequence_number` de placements cuyas
celdas se solapan con las de `box` — un sobre-conjunto barato de
"posibles vecinos", nunca un sub-conjunto (no puede producir falsos
negativos: cualquier par de cajas que realmente se solapen
comparte al menos una celda).

`rules/spatial_rules.py::evaluate_collision`,
`rules/stack_levels.py::find_direct_supporting_placements` (soporte) y
`rules/fragility_rules.py::evaluate_fragility` consultan `SpatialIndex`
antes de comparar geometría exacta (`geometry/collision.py::boxes_overlap`,
`geometry/support.py::horizontal_overlap_area_cm2`) — el índice reduce
cuántas comparaciones geométricas exactas se hacen, nunca sustituye la
comparación exacta en sí. `optimization/state.py::PackingState`
mantiene un único `SpatialIndex` incremental por ejecución
(`_spatial_index`), poblado en `accept_placement`, nunca reconstruido
desde cero.

**Garantía de ausencia de falsos negativos**: verificada por
`tests/rules/test_spatial_index_equivalence.py`, que ejecuta los
mismos escenarios de referencia con y sin índice espacial y exige
exactamente el mismo `RuleEvaluation`/`PackingResult` en ambos casos —
no solo "que no falle", sino resultado idéntico. Confirmado también de
forma end-to-end en el caso real de 2000 unidades citado en
`docs/OptimizerPerformance.md` ("Fase OPT-16"/"Fase OPT-17"): mismo
resultado exacto (1397/2000 cargadas, 84,46 % de utilización, cero
colisiones/cajas flotantes/avisos) en múltiples repeticiones.

## Consecuencias

- El costo de colisión/soporte/apilamiento/fragilidad por candidato
  pasa de recorrer `existing_placements` completo (O(n)) a consultar
  únicamente los vecinos de celda cercanos — la mejora real medida en
  el caso de 2000 unidades fue de ~2973 s a ~552-960 s (fase OPT-16,
  tras corregir varios puntos que todavía no aprovechaban el índice
  correctamente pese a que ya existía).
- El propio índice no es, por sí solo, una garantía de rendimiento
  lineal: la fase OPT-16 encontró y corrigió varios puntos
  (`fragility_rules`, `context.nearby_existing_boxes`,
  `evaluate_collision`, `find_direct_supporting_placements`,
  `evaluate_loading_space_weight`) que seguían filtrando listas
  completas en O(n) para traducir el resultado barato del índice de
  vuelta a `Placement`/caja, en vez de indexar directamente por
  `sequence_number` — ver `CLAUDE.md`, bullet "Fase OPT-16", para el
  detalle completo de qué se corrigió.
- No se introduce ningún filtrado manual de `existing_placements` por
  proximidad espacial antes de construir `PlacementRuleContext` — el
  filtrado real pasa siempre por `SpatialIndex`, no por una heurística
  ad-hoc en `optimization`. Ver el bullet correspondiente en
  `CLAUDE.md`, invariantes del motor de optimización.
- `docs/ProductBacklog.md`, ítem OPT-11, se actualiza para reflejar que
  el índice espacial está implementado y en uso desde varias fases,
  con referencia a este ADR.
- Si en el futuro se necesita una estructura espacial distinta
  (p. ej. un R-tree para geometrías no ortoédricas), eso es una
  decisión nueva y explícita, con su propio ADR — este documento cubre
  únicamente la rejilla de hash espacial de celda fija ya implementada.
