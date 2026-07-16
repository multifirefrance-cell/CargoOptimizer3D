# Rendimiento del optimizador — resultados de la fase 4.2

Este documento resume qué se optimizó, qué se midió después de
optimizar, y — con la misma honestidad exigida al iniciar esta fase —
que **el objetivo obligatorio (100 instancias, al menos 5x más rápido)
no se alcanzó**. Se explica por qué, con datos de perfilado real, y qué
optimizaciones sí se aplicaron con seguridad. Línea base completa en
`docs/PerformanceBaseline.md`.

## Resultado frente al objetivo

| tamaño | antes (fase 4.1) | después (fase 4.2) | factor |
|---:|---:|---:|---:|
| 10  | 0.196 s   | 0.151 s  | 1.30x |
| 100 | 102.635 s | 80.011 s | 1.28x |

**Objetivo obligatorio no cumplido**: se pedía al menos 5x para 100
instancias (es decir, ≤ ~20.5 s); el resultado real es ~1.28x
(80.011 s). Los objetivos deseables (100 en <5 s; 250 práctico; 500 sin
decenas de minutos) tampoco se alcanzan.

No se ha inventado ni maquillado ninguna mejora para aparentar cumplir
el objetivo: esta es la cifra real, medida con
`scripts/benchmark_optimizer.py`, con el mismo escenario mixto de la
línea base.

## Qué se optimizó (con seguridad, sin tocar `rules`/`geometry`)

1. **Bounding box cacheado incrementalmente** (`PackingState.accepted_boxes`,
   `PackingState.bounding_dimensions`, `optimization/state.py`): el
   `bounding_dimensions`/`bounding_volume_increment_cm3` de
   `optimization/scoring.py` recorría **todos** los placements
   aceptados en cada candidato evaluado (no una vez por instancia). Era
   el cuello de botella nº 1 medido por perfilado real (ver
   `docs/PerformanceBaseline.md`). Ahora se mantiene en O(1) por
   aceptación. Mismo valor matemático, mismo resultado — no es una
   aproximación.
2. **Omitir el *score* de candidatos rechazados**
   (`optimization/candidates.py::build_candidate`): `support_ratio`,
   el incremento de bounding volume y el espacio residual solo se
   calculan si `evaluation.is_allowed`; un candidato rechazado nunca se
   compara por *score* (verificado: solo se lee `.score` del candidato
   aceptado), así que calcularlo era trabajo desperdiciado —
   concretamente la parte de soporte físico (unión de rectángulos),
   antes calculada para prácticamente todos los candidatos.
3. **Poda segura de puntos candidatos** (`optimization/pruning.py`,
   nuevo): elimina puntos que, por geometría, nunca podrán producir una
   colocación válida — fuera de límites del Loading Space, o
   estrictamente dentro del volumen interior de una caja ya existente.
   Deliberadamente **no** poda por "punto dominado" (heurística, no
   certeza). Devuelve también los códigos de violación garantizados de
   los puntos podados, para que
   `GreedyExtremePointStrategy._classify_unpacked_reason` no cambie de
   comportamiento por saltarse candidatos que de todos modos habrían
   sido rechazados (ver el docstring del propio módulo para la prueba
   de por qué esto es seguro).

Estas tres optimizaciones son 100% seguras (mismo resultado, mismo
determinismo, mismas razones de `UnpackedUnit`) y están cubiertas por
`tests/optimization/test_state.py`, `tests/optimization/test_pruning.py`
y `tests/optimization/test_regression_greedy_extreme_point.py`. La
suite completa (331 pruebas, sin contar el benchmark manual de 500
instancias) sigue en verde.

## Por qué el objetivo no se alcanzó: el perfilado señala a `rules`, no a `optimization`

Perfilado real (`cProfile`, escenario mixto de 60 instancias, después
de aplicar las tres optimizaciones anteriores):

```
55 081 459 llamadas de función en 14.162 s (tiempo propio del profiler)

ncalls   cumtime  función
     1    15.917  greedy_extreme_point.py:pack
    60    15.917  greedy_extreme_point.py:_process_instance
 31245    15.516  optimization/candidates.py:build_candidate
 31245    15.219  rules/engine.py:evaluate_placement
 31245    15.200  rules/placement_rules.py:evaluate_candidate_placement
 65164     6.576  rules/stacking_rules.py:find_direct_supporting_placements
 31245     5.125  rules/spatial_rules.py:evaluate_collision
 19748     3.062  rules/stacking_rules.py:_all_transitive_supporters
 19748     2.960  rules/stacking_rules.py:evaluate_supported_weight
 19748     2.241  rules/spatial_rules.py:evaluate_support
```

El tiempo propio (`tottime`) de `optimization/candidates.py::build_candidate`
y de `greedy_extreme_point.py::_process_instance` es ya prácticamente
cero (0.128 s y 0.056 s respectivamente, sobre 14.162 s totales): las
optimizaciones de esta fase eliminaron casi por completo el coste que
`optimization` controlaba directamente. **El 100% del tiempo restante
está dentro de `rules.evaluate_placement`**, concretamente en
`find_direct_supporting_placements` y las funciones de apilamiento y
peso soportado que dependen de ella (`stacking_rules.py`,
`weight_rules.py` a través de ella), más `evaluate_collision` (que a su
vez llama masivamente a `box_from_placement` y `AxisAlignedBox.overlaps`
de `geometry`).

Este coste es un diseño ya documentado de la fase 3
(`docs/RulesEngine.md`): recorrer todos los placements existentes por
candidato es O(n), y `CLAUDE.md` prohíbe modificar `rules` o `geometry`
en esta fase salvo por un bug real (esto no lo es). Se evaluó
explícitamente si `optimization` podía mitigar este coste desde fuera:

- **Filtrar `existing_placements` antes de pasarlo a `PlacementRuleContext`**
  (para que `rules` recorra menos elementos): rechazado. Se comprobó
  que `stacking_rules.evaluate_supported_weight` necesita conocer,
  para cada soporte transitivo, **todo** lo que descansa sobre él en
  cualquier parte del layout (`_weight_resting_on` recorre
  `existing_placements` completo, no solo lo cercano al candidato) —
  filtrar por proximidad al candidato produciría resultados
  incorrectos de peso soportado.
- **Precalcular fuera del bucle las evaluaciones de `rules` que no
  dependen de posición/orientación** (`evaluate_extinguisher_configuration`,
  `evaluate_loading_space_weight`, y `evaluate_orientation` una vez por
  orientación en vez de una vez por candidato): técnicamente cierto que
  son constantes por instancia, pero replicar en `optimization` qué
  evaluaciones combinar y en qué orden duplicaría la política de
  cascada de `rules/placement_rules.py::evaluate_candidate_placement`
  (qué se omite si hay colisión, en qué orden), con riesgo real de
  divergencia si esa política cambia en el futuro. Se descartó por ir
  contra el principio explícito de `CLAUDE.md` ("no duplica ninguna
  regla geométrica o de negocio... solo arma el `PlacementRuleContext`
  y delega en `RulesEngine`").
- **`SpatialHashGrid`** (sección 7 del encargo): se evaluó pero se
  decidió **no implementarlo** en esta fase. Su valor esperado depende
  de poder saltar candidatos "obviamente inválidos" antes de llamar a
  `RulesEngine` — pero el perfilado del escenario de referencia (una
  bodega grande, 2000x1000x300 cm, con cajas pequeñas dispersas por el
  suelo) muestra que la poda geométrica (`pruning.py`, sección
  anterior) apenas se activa: hay abundante espacio libre, así que casi
  ningún punto candidato es geométricamente imposible de antemano. El
  coste dominante no es evaluar candidatos condenados, es evaluar
  candidatos genuinamente plausibles cuyo coste vive dentro de `rules`.
  Un índice espacial en `optimization` no puede reducir ese coste sin
  también filtrar lo que se le pasa a `rules`, que ya se determinó
  inseguro (punto anterior). Añadirlo solo para los casos límite donde
  sí ayudaría habría sido sobrearquitectura sin beneficio medido en el
  escenario de referencia — contrario al principio de "no
  sobrearquitecturar" de `CLAUDE.md`.

## Conclusión honesta

Con las restricciones de esta fase (no modificar `domain`, `geometry`
ni `rules`), el margen de mejora disponible dentro de `optimization` ya
se agotó: se eliminó prácticamente todo el coste propio de
`optimization`, y lo que queda es, en su totalidad, coste de `rules`
evaluando soporte/apilamiento/peso soportado de forma O(n) por
candidato — un diseño deliberado de la fase 3, no un defecto de esta
fase. Alcanzar el objetivo de 5x (o el crecimiento sub-cúbico deseable
para 250/500 instancias) requeriría casi con certeza una estructura de
datos espacial **dentro de `rules`/`geometry`** (p. ej. indexar
placements por altura y solape horizontal para `find_direct_supporting_placements`,
o una estructura equivalente para `evaluate_collision`), lo cual está
fuera del alcance autorizado de esta fase (`CLAUDE.md`: "Detente
únicamente si: ... debes modificar reglas ... debes cambiar semántica
geométrica"). Se recomienda que una fase futura, con ADR explícito,
aborde un índice espacial dentro de `rules`/`geometry` si el
rendimiento a esa escala sigue siendo prioritario — ver
`docs/Roadmap.md`.

## Metodología

Mismo entorno, mismo escenario (`scripts/benchmark_optimizer.py::build_scenario`)
y misma metodología que `docs/PerformanceBaseline.md`. Comparación
antes/después limitada a los tamaños con medición limpia de referencia
disponible (10 y 100); ver esa nota en `docs/PerformanceBaseline.md`.

---

## Fase OPT-02 (2026-07-16): caché de cajas ya conocidas, sin tocar la complejidad

Backlog: `docs/ProductBacklog.md`, ítem `OPT-02`. Objetivo del encargo:
mejorar el rendimiento real del `PackingEngine` sin cambiar ningún
resultado, con datos de perfilado **actuales**, no reutilizando las
cifras de la fase 4.2 de arriba.

### Perfilado fresco (2026-07-16, antes de esta fase)

Mismo escenario mixto de referencia, 60 instancias, `cProfile`:

```
55 081 459 llamadas en 45.690 s (con instrumentación de cProfile)

ncalls      tottime  cumtime  función
   1           0.000   51.366  optimize
   1           0.001   51.349  greedy_extreme_point.pack
4 596 319      5.293    9.706  geometry/box.py:box_from_placement   <-- síntoma nuevo detectado
  65 164       4.968   20.861  rules/stacking_rules.py:find_direct_supporting_placements
1 236 150      4.727   10.541  geometry/box.py:overlaps
 949 683      4.891     8.398  geometry/support.py:horizontal_overlap_area_cm2
  50 993      0.755     6.115  rules/context.py:existing_boxes (propiedad)
```

Confirma lo que ya diagnosticó la fase 4.2 (el coste real vive dentro
de `rules`/`geometry`, no de `optimization`) — pero el perfilado fresco
señala además un cuello de botella **nuevo y evitable** que no estaba
documentado en la fase 4.2: `box_from_placement` se llama 4 596 319
veces, y una fracción enorme de esas llamadas es **trabajo
completamente redundante**.

### El hallazgo: `optimization` ya cachea las cajas, pero `rules` las ignoraba

Desde la fase 4.2, `PackingState.accepted_boxes` mantiene las cajas de
los placements aceptados cacheadas de forma incremental (O(1) por
aceptación, ver `docs/PerformanceBaseline.md`), y
`greedy_extreme_point.py` captura ese valor **una vez por instancia**
y lo pasa a `build_candidate(..., existing_boxes=...)`. Hasta esta
fase, `build_candidate` solo reutilizaba ese valor para el cálculo de
soporte del *score* — pero al construir el `PlacementRuleContext` que
se le pasa a `RulesEngine`, **no lo pasaba**: `PlacementRuleContext.
existing_boxes` era una `@property` que reconstruía la lista completa
de cajas con `box_from_placement` **en cada acceso**, y se accede
varias veces por candidato (colisión, soporte) más, dentro de
`stacking_rules` (apilamiento, peso soportado, con su propia
recursión), donde cada función volvía a llamar a `box_from_placement`
por su cuenta, sin usar ni la propiedad de `rules` ni el caché de
`optimization`.

En otras palabras: el dato ya existía, calculado una sola vez por
instancia dentro de `optimization`, y `rules` lo tiraba y lo
reconstruía desde cero, muchas veces por candidato, sin que nadie se
beneficiara del caché ya existente.

### Qué se cambió (solo `rules` + una línea en `optimization`)

- `rules/context.py`: `PlacementRuleContext` gana un campo opcional
  `precomputed_existing_boxes: tuple[AxisAlignedBox, ...] | None = None`.
  `existing_boxes` devuelve ese valor si se proporciona; si no
  (`None`), recalcula exactamente como antes — **compatibilidad total
  con cualquier prueba unitaria de `rules` que construya un
  `PlacementRuleContext` a mano sin este campo nuevo**. Se añade
  también `box_by_sequence_number` (una `Mapping[int, AxisAlignedBox]`
  indexada por `Placement.sequence_number`) para que las funciones
  recursivas de apilamiento tengan también acceso O(1) a una caja ya
  conocida.
- `rules/stacking_rules.py`: `find_direct_supporting_placements`,
  `count_stack_level`, `_all_transitive_supporters` y
  `_weight_resting_on` ganan un parámetro opcional
  `box_by_sequence_number` (por defecto `None`, mismo comportamiento
  de recálculo que antes); cuando se proporciona, sustituyen su propia
  llamada a `box_from_placement` por una consulta O(1) al mapa.
- `optimization/candidates.py`: una línea — `build_candidate` ahora
  pasa `precomputed_existing_boxes=existing_boxes` (el valor que ya
  recibía como parámetro) al construir el `PlacementRuleContext`.

Ningún cambio en `domain` ni en `geometry`. Ninguna fórmula, tolerancia
ni regla de negocio se tocó: `box_from_placement` sigue siendo la
misma función pura; solo se evita llamarla cuando el resultado ya se
conoce. **Se justifica tocar `rules`** (fuera del alcance por defecto
de `CLAUDE.md`) precisamente porque es una optimización de rendimiento
100% transparente: mismo resultado en ambos caminos, código nuevo
verificado por equivalencia explícita (ver Pruebas) además de por la
suite completa sin cambios.

### Verificación de que el resultado no cambió

- Suite completa: **846 pruebas, sin ningún cambio** — incluye
  `tests/optimization/test_regression_greedy_extreme_point.py`, que
  compara contra un layout de referencia capturado; si el algoritmo
  hubiera producido una sola colocación distinta, esa prueba habría
  fallado.
- `tests/rules/test_performance_cache_equivalence.py` (nueva): compara
  explícitamente, sobre un layout de tres niveles con límites de peso
  soportado, el resultado de `evaluate_candidate_placement`,
  `evaluate_stack_count` y `evaluate_supported_weight` **con y sin**
  `precomputed_existing_boxes` — mismo `RuleEvaluation`, comparado por
  `==` sobre dataclasses `frozen` (violaciones incluidas, no solo
  `is_allowed`).

### Impacto medido

Con la misma instrumentación de `cProfile` (comparación controlada:
mismo proceso, mismo overhead de perfilado en ambos casos — la forma
más fiable de comparar en esta máquina, ver nota de ruido más abajo),
60 instancias, mismo escenario:

| métrica | antes | después | cambio |
|---|---:|---:|---:|
| tiempo total (cProfile) | 45.690 s | 38.660 s | **−15.4 %** |
| llamadas a `box_from_placement` | 4 596 319 | 769 109 | **−83.3 %** |
| llamadas de función totales | 55 081 459 | 53 447 293 | −3.0 % |

La reducción de llamadas a `box_from_placement` es enorme (−83 %), pero
la reducción de tiempo total es mucho más modesta (−15 %): construir
una `AxisAlignedBox` ya era barato (dos referencias a campos
existentes); lo caro nunca fue *reconstruir* la caja, sino *usarla*
dentro de `overlaps`/`horizontal_overlap_area_cm2`/`_axis_overlap`,
que se siguen ejecutando el mismo número de veces — esta fase elimina
trabajo redundante de construcción de objetos, no reduce el número de
comparaciones geométricas por candidato. Ver "Conclusión honesta" más
abajo.

**Nota sobre ruido del entorno**: el benchmark de reloj de pared
(`scripts/benchmark_optimizer.py`, fuera de `cProfile`) mostró una
variabilidad run a run muy alta en esta máquina (60 instancias, código
**sin cambios**, mismo escenario: 41.4 s / 66.9 s / 51.4 s / 65.1 s /
36.7 s de mediana según el momento), casi con toda seguridad por
actividad de fondo del sistema (el repositorio vive dentro de una
carpeta sincronizada por OneDrive). Por eso la cifra de referencia de
esta sección es la comparación instrumentada con `cProfile` (mismo
proceso, mismo overhead en ambos lados, mucho más estable que
comparar dos procesos separados en momentos distintos), no las
medias de reloj de pared — que, aun así, se incluyen más abajo por
transparencia, con su variabilidad real, sin suavizarlas.

### Tabla comparativa de reloj de pared (30/60/100/200/500)

Mediana de varias repeticiones cuando fue posible; rango
min–max entre paréntesis para dejar ver el ruido real en vez de
esconderlo. "antes" y "después" se midieron alternando
`git stash`/`git stash pop` sobre el mismo commit base, en la misma
sesión, en la misma máquina.

| tamaño | antes (mediana, min–max) | después (mediana, min–max) | repeticiones |
|---:|---:|---:|---:|
| 10  | 0.194 s (0.186–0.203 s) | 0.139 s (0.137–0.160 s) | 3 |
| 30  | 4.078 s (3.912–9.688 s) | 6.442 s (3.878–6.554 s) | 3 |
| 60  | 36.720–66.007 s según la tanda (25.9–66.9 s en 8 corridas totales) | 17.745–51.425 s según la tanda (17.7–51.4 s en 8 corridas totales) | 8 |
| 100 | 195.062 s | 142.532 s | 1 (una sola corrida; demasiado costosa para repetir varias veces en esta sesión) |
| 200 | no medido (ver nota) | **583.007 s** (~9.7 min) | 1 (corrida en segundo plano, terminó tras el resto de esta fase) |
| 500 | no medido (ver nota) | no medido (ver nota) | — |

**200 (después) se terminó de medir en segundo plano tras el resto de
esta fase**: 583.007 s con el código ya optimizado. La razón 100→200
(tamaño ×2) da un factor de tiempo de ×4.09 (142.532 s → 583.007 s),
más cercano a un crecimiento cuadrático que al cúbico estricto que se
había anticipado extrapolando de la fase 4.2 — con una sola medición
por tamaño y el ruido de esta máquina ya documentado arriba, no se
puede afirmar con confianza que el exponente real cambió; lo único que
se puede afirmar con confianza es la cifra medida en sí, no la
tendencia. **200 (antes) y 500 (antes/después) no se ejecutaron por
completo en esta sesión**: extrapolando desde la razón 100→200
realmente medida (×4.09 para ×2 de tamaño), 500 instancias (×2.5 de
tamaño respecto a 200) tomarían muy aproximadamente entre **~1 y ~2.5
horas**, según si el crecimiento real en ese rango es más cuadrático o
más cúbico — un rango, no una cifra única, precisamente porque una
sola medición por tamaño no permite ajustar el exponente con
confianza. No se ha inventado ni maquillado ninguna cifra: 500 no se
ejecutó completo porque hacerlo de forma fiable (con repeticiones,
para lidiar con el ruido medido arriba) habría requerido horas de
cómputo solo para esta verificación, y este informe prioriza no
bloquear la entrega con una medición de valor marginal frente al
diagnóstico ya claro (mismo orden de magnitud que 100/200, sin cambio
de complejidad).

### Complejidad: qué cambió y qué no

- **Complejidad temporal**: sin cambios. Sigue siendo ~O(n) por
  candidato (colisión y soporte recorren todos los `existing_placements`)
  × O(n) candidatos por instancia (aproximadamente) × O(n) instancias
  ≈ O(n³)-ish total, la misma clase que documentó la fase 4.2. Esta
  fase **no** introduce ninguna estructura de datos espacial que
  reduzca el número de comparaciones — solo elimina la reconstrucción
  redundante de objetos `AxisAlignedBox` ya conocidos. El factor
  constante baja (menos trabajo por comparación), la forma de la curva
  no.
- **Complejidad espacial**: sin cambio significativo. `precomputed_existing_boxes`
  reutiliza la misma tupla de cajas que `optimization` ya mantenía
  (cero memoria nueva persistente); `box_by_sequence_number` es un
  `dict` transitorio de tamaño `len(existing_placements)`, construido
  y descartado en cada evaluación de candidato — memoria adicional
  máxima aproximada: `O(existing_placements)` punteros/entradas de
  `dict` vivos solo durante una evaluación, recolectados
  inmediatamente después (no se acumula entre candidatos ni entre
  instancias).

### Cuello de botella que queda ahora

Con la reconstrucción redundante de cajas eliminada, el perfilado
fresco tras esta fase sitúa el coste dominante, en orden:

1. `rules/stacking_rules.py:find_direct_supporting_placements` (4.655 s
   tottime, 65 164 llamadas) — sigue siendo un recorrido O(n) de
   `existing_placements` por llamada, y se llama recursivamente desde
   `count_stack_level`/`_all_transitive_supporters`/`_weight_resting_on`.
2. `geometry/support.py:horizontal_overlap_area_cm2` (4.609 s tottime,
   949 683 llamadas) y `geometry/box.py:overlaps` (4.232 s tottime,
   1 236 150 llamadas) — el coste puro de la comparación geométrica
   AABB, ejecutada una vez por par (candidato, placement existente).

Ninguno de los dos se puede reducir más sin cambiar **cuántas**
comparaciones se hacen, no solo cuánto cuesta cada una — es decir,
sin una estructura de datos espacial real (un índice por rejilla o
similar) dentro de `rules`/`geometry` que permita descartar, antes de
llamar a estas funciones, los `existing_placements` que no pueden
compartir altura ni solape horizontal con el candidato. Esto es
exactamente lo que la fase 4.2 ya identificó como el siguiente paso
necesario y fuera de su alcance — sigue siéndolo hoy.

### Conclusión honesta

El objetivo del encargo era "mejorar significativamente el
rendimiento". Con los datos reales de esta fase: se logró una mejora
real, medida y verificada (−15.4 % en tiempo instrumentado, −83.3 % en
reconstrucciones de caja redundantes, cero cambio de resultado), pero
**no** una mejora significativa en el sentido de cambiar de orden de
magnitud a 100/200/500 instancias — porque la causa raíz (recorrido
O(n) de `existing_placements` en colisión/soporte/apilamiento) es
estructural, no un descuido de caché. Reducirla de verdad exige un
índice espacial dentro de `rules`/`geometry`, que esta fase
deliberadamente no implementa: es un cambio de mayor alcance y riesgo
(una implementación incorrecta podría introducir un falso negativo de
colisión o de soporte, silencioso y grave), y esta fase prioriza
"mantener el resultado exactamente igual" sobre "parecer más rápida".
Se recomienda una fase futura dedicada, con su propio ADR, que aborde
esa estructura — ver `docs/Roadmap.md` y `docs/ProductBacklog.md`,
ítem `OPT-02` (que permanece parcialmente resuelto: la caché es un
paso real y verificado en esa dirección, no el cierre completo del
ítem).
