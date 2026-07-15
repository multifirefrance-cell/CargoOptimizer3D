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
