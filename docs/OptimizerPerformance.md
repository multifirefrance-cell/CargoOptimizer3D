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

---

## OPT-03 → OPT-11 (2026-07-17): confirmación con un caso real, investigación cerrada sin código

Un usuario reportó, en la interfaz real, un caso concreto: al pedir
1300 unidades de una caja de 20×20×50 cm (9 kg, apilamiento hasta 30
niveles) en un contenedor de 20 pies, solo se cargaron 148 antes de
que el usuario cancelara la ejecución tras ~15 s, con el 91.1% del
volumen y el 95.3% del peso todavía disponibles. Dos preguntas
distintas, mismo origen:

1. **"¿Por qué solo 148 de 1300?"** — no es un límite de volumen/peso
   (solo 8.9% de volumen y 4.7% de peso usados); es que el algoritmo
   agota su capacidad práctica de encontrar más colocaciones válidas en
   un tiempo razonable antes de completar el intento.
2. **"¿Por qué 'Ejecutar optimización' parece no hacer nada y solo
   aparece un resultado al cancelar?"** — el cálculo sí está
   corriendo (la barra de progreso avanza), pero para una cantidad tan
   grande, completar naturalmente el intento sobre todas las unidades
   que terminan sin caber toma mucho más tiempo del que un usuario
   espera razonablemente. Cancelar es, hoy, la única forma práctica de
   obtener un resultado utilizable en poco tiempo para este caso.

**Perfilado real (`cProfile`) del mismo escenario, reducido a 300
unidades** (todas caben sin desbordar, precisamente para poder medir
algo completable en una sesión):

```
2 184 133 573 llamadas de función en 1262.476 s (tiempo instrumentado)

ncalls      tottime  función
54 529 308   566.588  geometry/collision.py:boxes_overlap
   634 806   105.133  rules/stacking_rules.py:find_direct_supporting_placements
35 499 546    79.593  geometry/support.py:horizontal_overlap_area_cm2
54 529 308    58.037  geometry/box.py:overlaps
   211 953    38.844  geometry/support.py:support_area_cm2
```

**~21 minutos para 300 instancias que caben sin problema** (packed=300,
unpacked=0) — confirma, con datos frescos y un escenario distinto (caja
pequeña, apilamiento profundo hasta 30 niveles, muchas colocaciones
acumuladas) al de las fases 4.2/OPT-02 anteriores (bodega grande, cajas
dispersas), el mismo diagnóstico: el costo dominante es la comprobación
O(n) de colisión/soporte contra **todos** los `existing_placements`,
y crece de forma no lineal a medida que se acumulan más cajas
colocadas — no importa si el escenario de referencia es "cajas
dispersas en una bodega" o "apilamiento denso en un contenedor
pequeño": el mecanismo de fondo (recorrido O(n) sin índice espacial)
es el mismo, y ambos lo confirman de forma independiente.

**Decisión explícita del arquitecto del proyecto (2026-07-17):**
cerrar esta investigación aquí, sin escribir código, sin modificar
`domain`/`geometry`/`rules`/`optimization`, y sin redactar todavía el
ADR del índice espacial — la evidencia ya reunida (aquí y en las
secciones anteriores) es suficiente para tomar la decisión técnica
cuando se retome. El ítem queda formalizado en `docs/ProductBacklog.md`
como **OPT-11 — Índice espacial para colisión/soporte (postergado, sin
ADR)**, con el problema, las métricas, el riesgo de falsos negativos
de colisión/soporte, y la razón explícita de la postergación. La
prioridad vuelve por completo al desarrollo funcional de la Beta 1.0;
no se abrirán nuevas investigaciones de rendimiento hasta que esa Beta
esté funcionalmente terminada.

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

## Fase OPT-17 (2026-07-18): patrón de filas/capas, orientaciones por defecto reducidas, caché de `support_ratio`

Fase integrada de un solo encargo: orientaciones por defecto más
simples para SKU nuevos, carga por patrón (filas/capas) para
cantidades grandes del mismo SKU, reutilización del `support_ratio` ya
calculado dentro de un mismo candidato, y colores pastel
automáticos/selector manual (esto último sin impacto de rendimiento,
documentado en `docs/Database.md`/`docs/ProjectFiles.md`, no aquí).
Ninguno de los cambios ya aceptados de las fases OPT-02 a OPT-16 se
revirtió: índice espacial, cachés incrementales, early-exit exacto,
memoización de posiciones candidatas, preferred orientation,
empaquetado en dos rondas, simplificación de apilamiento, eliminación
de peso soportado acumulado y de apilamiento recursivo — todo sigue
intacto.

### Qué se añadió

1. **Orientaciones por defecto reducidas** (`domain/load_unit.py::DEFAULT_ORIENTATION_CODES`):
   un `LoadUnit` nuevo sin `allowed_orientation_codes` explícito ahora
   recibe solo `LWH_XYZ` y `WLH_XYZ` (las dos únicas orientaciones que
   mantienen `height_cm` en el eje Z) en vez de las 6. Un producto ya
   configurado (incluidos los que ya declaraban las 6) nunca se toca al
   editarlo — la reducción es solo el valor por defecto del campo, no
   una migración de datos existentes.
2. **Patrón de filas/capas** (`optimization/pattern_packing.py`,
   nuevo): para un `LoadUnit` con `quantity >= 8`, tras colocar la
   primera instancia con la búsqueda completa habitual (que actúa como
   "ancla" real, ya validada por `RulesEngine`), las siguientes
   instancias de la misma ronda 1 intentan **un único candidato** por
   turno — la siguiente posición de una rejilla regular
   (`generate_grid_positions`, fila completa en X, luego fila en Y,
   luego capa en Z) — en vez de repetir la búsqueda completa de
   extremos. Ese único candidato pasa por
   `RulesEngine.evaluate_placement` completo, sin ningún atajo de
   corrección: si falla (colisión, rejilla agotada, cualquier regla),
   el patrón se marca agotado para ese `LoadUnit` de forma permanente y
   **todas** las instancias restantes caen a la búsqueda general
   exactamente como si el patrón no hubiera existido nunca. Este diseño
   hace que el patrón no pueda, por construcción, producir un resultado
   peor que el algoritmo anterior: en el peor caso se comporta
   idéntico a él.
3. **Reutilización de `support_ratio` dentro de un mismo candidato**
   (`rules/context.py::PlacementRuleContext.precomputed_support_ratio`,
   `optimization/candidates.py::build_candidate`): antes de esta fase,
   la unión de rectángulos que calcula el soporte se ejecutaba dos
   veces por candidato aceptado — una dentro de
   `rules/spatial_rules.py::evaluate_support` (para decidir si hay
   soporte suficiente) y otra en `build_candidate` (para puntuar el
   candidato). Ahora se calcula una sola vez, solo cuando ya se sabe
   que el candidato no colisiona (`evaluate_collision`, barato gracias
   al índice espacial), y se reutiliza para ambos propósitos. Sin
   `precomputed_support_ratio` (toda prueba unitaria que construye un
   `PlacementRuleContext` a mano), el comportamiento es idéntico al de
   antes de esta fase.
4. **Render 3D auditado, sin cambios**: se confirmó que
   `GreedyExtremePointStrategy._emit_progress` solo construye un
   `PackingProgress` (contadores, ningún objeto de Qt/PyVista) y que
   `MainWindow._on_optimization_progress` solo actualiza la barra de
   progreso — `Packing3DViewer.display_result(...)` se sigue llamando
   una única vez, tras `_on_optimization_finished`, nunca dentro del
   bucle de optimización. No hizo falta ningún cambio de código.

### Medición del caso real (`cargo2500.cargo3d`, 2000 unidades, mismo SKU)

Corrección idéntica en las **tres** repeticiones —
1397/2000 cargadas, 603 pendientes, 84,4589 % de utilización, cero
colisiones, cero cajas fuera de límites, cero cajas flotantes, cero
avisos —, confirmando que ninguno de los cambios de esta fase alteró
ninguna decisión del algoritmo, solo (en principio) su coste:

| Medición | Condición | Tiempo | vs. baseline (552,30 s) |
|---|---|---:|---|
| Baseline (fin de OPT-16) | — | 552,30 s | — |
| Aislada, justo tras implementar el patrón (antes de sumar la caché de `support_ratio`) | sin otros procesos detectados | 472,73 s | 14,4 % más rápido (1,17×) |
| "Limpia" según el protocolo pedido (sin pytest ni otro benchmark en paralelo), con la caché de `support_ratio` ya incluida | con una instancia residual de `CargoOptimizer3D`, Chrome y Dropbox activos en el sistema durante la medición | 1362,77 s | 146,7 % más lento (0,41×) — **descartada como oficial** |

**El speedup final de esta fase queda pendiente de confirmar en una
máquina descargada.** La segunda medición "limpia" (sin procesos de
prueba propios corriendo) coincidió con otros procesos del sistema
operativo activos que no se controlaron ni se cerraron antes de medir,
y su tiempo es indistinguible de contención de CPU ajena al código: el
resultado del algoritmo fue exactamente igual en las tres ejecuciones
(mismo `packed_count`, misma utilización, cero avisos), lo que descarta
un defecto de corrección o una regresión algorítmica real, pero no
permite descartar contención como causa del tiempo alto. La única cifra
de espera medida en condiciones verificadamente aisladas
(472,73 s, 14,4 % más rápida) no incluye todavía la caché de
`support_ratio` de esta misma fase. No se debe citar ningún número de
"×" de esta fase como definitivo hasta repetir la medición en una
máquina sin otras aplicaciones activas — ver `docs/Roadmap.md`.

## Fase OPT-16 (2026-07-18): caso real de 2000 unidades — de ~2973 s a ~552-960 s, mismo resultado exacto

Caso real reportado: contenedor 20' (589×235×239 cm, 28180 kg), un
único SKU "111107" (50×20×20 cm, 1 kg, `quantity=2000`,
`max_stack_count=30`). Resultado previo a esta fase: 1397/2000
cargadas (84,46 % de utilización), 2972,83 s (~49,5 min).

### Pregunta 1: ¿1397 es la capacidad máxima razonable?

Capacidad teórica por volumen puro (sin geometría): 33 081 185 cm³ /
20 000 cm³ ≈ 1654 unidades — un límite que ninguna heurística de
bin-packing real alcanza (problema NP-duro). Mejor rejilla regular de
una sola orientación calculada a mano (las 3 permutaciones de
50×20×20 sobre 589×235×239): 1331 (orientación con 50 cm sobre X, 11
niveles de 20 cm de alto). El resultado real (1397) **ya supera esa
rejilla regular** gracias al empaquetado en dos rondas con orientación
preferida (fase previa, 2026-07-17): la ronda 1 tesela con la
orientación que `select_preferred_orientation` elige — maximizar
`floor(largo/x) × floor(ancho/y)` de una sola capa (footprint
20×20, 319 unidades/capa × 4 capas de 50 cm = 1276) — y la ronda 2
añade ~121 unidades más en el hueco vertical residual (~39 cm) con
otra orientación (50×20 de footprint, 20 cm de alto). 1397/1654 ≈
84,4 % del límite volumétrico absoluto: un resultado sólido para una
heurística greedy real, no un error.

**Experimento realizado (rechazado, sin tocar el código fuente):**
se probó un `select_preferred_orientation` alternativo que maximiza
la teselación completa en 3 ejes (`floor(largo/x) × floor(ancho/y) ×
floor(alto/z)`, no solo XY) sobre este mismo caso real —
`docs/OptimizerPerformance.md` documenta el resultado para que ninguna
sesión futura repita el experimento sin necesidad: **1371/2000
cargadas, 26 unidades MENOS que la heurística actual.** La intuición
de que "maximizar la teselación en los 3 ejes debería ser siempre
mejor" es incorrecta en la práctica: la heurística actual (solo XY) +
la ronda 2 (todas las orientaciones sobre el remanente) ya superan al
cálculo XYZ "más informado" para este caso real. **No se modifica
`select_preferred_orientation`.**

### Pregunta 2: ¿por qué tardaba ~50 minutos?

Perfilado real (`cProfile`) a escala reducida (100/200/400/800
unidades) reveló un patrón sistemático: **el índice espacial de la
fase OPT-11 existía, pero varias reglas no lo aprovechaban
correctamente**, cada una con una variante del mismo antipatrón —
"traducir el subconjunto barato de `sequence_number` que devuelve el
índice de vuelta a objetos `Placement`/caja filtrando la lista
completa de `existing_placements`" (`O(n)` por candidato, pese a
tener el índice):

1. **`rules/fragility_rules.py::evaluate_fragility`** — el hallazgo
   más grave: llamaba a `find_direct_supporting_placements` **sin
   pasar el índice espacial ni el mapa `box_by_sequence_number`**,
   así que reconstruía la caja de **todos** los `Placement`
   existentes (`box_from_placement`, geometría real) en cada
   candidato evaluado, sin excepción. Con el SKU de este caso real
   (`fragile=False`), la regla nunca rechazaba nada — todo ese
   recorrido era 100 % trabajo desperdiciado. Corregido: ahora recibe
   los mismos argumentos que `evaluate_stack_count`.
2. **`rules/context.py::nearby_existing_boxes`** y
   **`rules/spatial_rules.py::evaluate_collision`** — con índice
   disponible, seguían haciendo `zip(existing_placements,
   existing_boxes)` + filtro por pertenencia a `nearby` (`O(n)`) para
   traducir el subconjunto barato, en vez de indexar directamente vía
   `box_by_sequence_number` (`O(k)`, `k = len(nearby)`).
3. **`rules/stack_levels.py::find_direct_supporting_placements`** —
   mismo patrón: `_nearby_placements` filtraba `existing_placements`
   completo en vez de traducir `nearby` vía un mapa
   `placement_by_sequence_number` (campo nuevo, mantenido
   incrementalmente por `PackingState`, igual que
   `box_by_sequence_number`).
4. **`rules/weight_rules.py::current_loaded_weight_kg`** — sumaba el
   peso de `existing_placements` completo en cada candidato, sin
   ningún índice posible (el peso no es espacial): se sustituyó por un
   total incremental (`PackingState._packed_weight_kg`, actualizado en
   `accept_placement`), pasado como `precomputed_total_weight_kg`.
5. **Corte temprano exacto en `GreedyExtremePointStrategy._search_best_candidate`**:
   `positions` ya llega ordenado ascendentemente por `(z, x, y)`
   (`geometry/candidate_points.py`), y `score_candidate` compara
   exactamente `(z, x, y, ...)` en ese mismo orden como sus tres
   primeros componentes (`optimization/scoring.py`). Como las
   posiciones son estrictamente crecientes en ese orden tras el
   deduplicado, ningún candidato en una posición posterior puede
   ganarle en score a un candidato ya válido en una posición anterior
   — se prueban todas las orientaciones de la posición actual (que sí
   pueden desempatar entre sí) y, en cuanto alguna resulta válida, se
   deja de recorrer posiciones posteriores. No es la heurística de
   "punto dominado" que `pruning.py` descarta explícitamente (esa
   comparaba candidatos entre sí de forma aproximada); es una
   consecuencia matemática exacta del propio orden del score, sin
   ninguna aproximación — confirmado porque el resultado final
   (1397/2000, mismo peso, misma utilización) no cambió en ninguna
   escala probada.
6. **Memoización de puntos candidatos** (`PackingState.cached_pruned_candidate_positions`):
   `generate_candidate_positions` + `prune_candidate_positions` solo
   pueden cambiar de resultado cuando cambia el conjunto de placements
   aceptados — dos intentos de colocación consecutivos sin ninguna
   aceptación de por medio (todo el tramo final de la ronda 2, cuando
   la mayoría de las 603 unidades pendientes fallan una tras otra sin
   que nada cambie) recalculaban antes exactamente los mismos puntos.
   Se invalida comparando `len(_placements)` con la última versión
   calculada.

### Resultado medido

Mismo resultado exacto en las tres repeticiones del caso real
(1397/2000 cargadas, 1397 kg, 84,46 % de utilización,
`unpacked reasons: {'no_feasible_position': 603}` en las tres) —
confirma que ninguna de las correcciones anteriores cambió ninguna
decisión del algoritmo, solo su coste:

| Ejecución | Tiempo |
|---|---|
| Antes de esta fase | 2972,83 s (~49,5 min) |
| Después (máquina sin otra carga) | 552,30 s (~9,2 min) — **5,4×** |
| Después (máquina con otras pruebas en paralelo) | 872,90 s / 962,81 s (~14-16 min) — **3,1-3,4×** |

El nuevo cuello de botella dominante (perfilado a escala reducida tras
todas las correcciones) es `rules/spatial_rules.py::evaluate_collision`
(~45 % del tiempo total) — geometría de colisión real
(`geometry.collision.boxes_overlap`) contra el subconjunto ya acotado
por el índice espacial, no un recorrido `O(n)` oculto. Es trabajo
genuino de verificación geométrica (imprescindible para garantizar
cero colisiones), correctamente localizado — no queda ningún
antipatrón conocido de los descritos arriba. Reducirlo más allá exige
tocar cuántos candidatos se generan por instancia (no cuánto cuesta
evaluar cada uno), un cambio de mayor alcance sobre el propio algoritmo
de búsqueda de `GreedyExtremePointStrategy`, fuera del alcance de esta
fase.

### Invariantes verificados sin excepción

Las tres ejecuciones completas del caso real terminaron sin lanzar
`OptimizationInternalError` — la validación final de
`PackingEngine.optimize()` (`geometry.layout_validation`, invocada
siempre al final, nunca omitida) es la garantía estándar de este
proyecto de que el layout resultante tiene cero colisiones, cero cajas
fuera del `LoadingSpace` y cero cajas sin soporte válido; no se
desactivó ni se relajó en ningún momento de esta fase. `max_stack_count`
del SKU (30), las 6 orientaciones permitidas y el peso máximo del
espacio (28180 kg, muy por encima de los 1397 kg reales) se siguieron
respetando exactamente igual que antes — no se reintrodujo peso
soportado acumulado, apilamiento recursivo, peso por eje ni centro de
gravedad en ningún punto.

## Fase OPT-15 (2026-07-18): eliminación de la excepción automática de apilamiento para extintores

No es un cambio de rendimiento: es la eliminación completa, a petición
explícita del arquitecto del proyecto, de una regla de negocio que ya
no debe existir.

Hasta esta fase, `rules/extinguisher_rules.py::effective_max_stack_count`
forzaba `max_stack_count` efectivo a `1` para cualquier extintor
individual >= 3 kg nominales (PQS, CO₂ o cualquier otro agente),
ignorando el valor que el usuario hubiera configurado en el SKU. Esa
función, su uso en `rules/stacking_rules.py::evaluate_stack_count`, su
método facade `RulesEngine.effective_max_stack_count`, y su
reexportación desde `rules/__init__.py`, se eliminaron por completo
(no se desactivaron ni se dejaron como no-op): ya no existe en el
código ninguna ruta que fuerce `max_stack_count=1` por ser extintor,
por agente PQS/CO₂, por peso nominal ni por `package_type=INDIVIDUAL`.

A partir de esta fase, `evaluate_stack_count` usa siempre
`load_unit.max_stack_count` directamente, sin excepción por tipo de
producto: un extintor individual >= 3 kg con `max_stack_count=1` sigue
sin ser apilable (mismo resultado práctico que antes, si el usuario
así lo configura), pero uno con `max_stack_count=5` o
`DEFAULT_MAX_STACK_COUNT` (30, ver "Fase OPT-14" más abajo) ahora sí
apila hasta ese límite, igual que cualquier otro `LoadUnit`.

**La regla de horizontalidad de extintores individuales >= 3 kg no se
toca**: `is_individual_large_extinguisher`,
`evaluate_extinguisher_orientation` y los códigos
`EXTINGUISHER_INDIVIDUAL_MUST_BE_HORIZONTAL`/
`EXTINGUISHER_AXIS_NOT_PARALLEL_TO_X` siguen exactamente igual — un
extintor individual >= 3 kg sigue sin poder colocarse en vertical, solo
deja de tener un límite de apilamiento distinto al de su propio SKU.
Tampoco se toca la regla de cajas grupales de 1/2/3 kg (orientación
libre, `max_stack_count` respetado tal cual desde antes de esta fase) ni
las advertencias de capacidad recomendada.

## Fase OPT-14 (2026-07-18): valor por defecto de `max_stack_count` para productos nuevos

`LoadUnit.max_stack_count` pasó de tener un valor por defecto de `1` a
`DEFAULT_MAX_STACK_COUNT` (30) para productos nuevos sin este campo
configurado explícitamente — origen real de un caso de cubicaje
deficiente reportado (162/300 unidades cargadas, causado por
`max_stack_count=1` accidental en ambos SKU del escenario real,
diagnosticado por instrumentación sin modificar el motor). Sigue siendo
un entero normal, sin sentinel ni valor especial reservado: el usuario
puede cambiarlo libremente a cualquier valor `>= 1` para cualquier SKU,
incluidos los extintores. Ver `docs/DomainModel.md` y el docstring de
`LoadUnit.max_stack_count` para el detalle completo.
