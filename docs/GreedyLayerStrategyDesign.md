# Diseño de la primera estrategia de empaquetado (Fase 4.0, ya implementada en 4.1)

Este documento es el diseño original de la fase 4.0. **La
implementación real ya existe**: `GreedyExtremePointStrategy`
(`src/cargo_optimizer/optimization/greedy_extreme_point.py`),
identificador `greedy_extreme_point_v1`, exactamente como se recomendó
aquí (extreme-point greedy, no *layering* estricto). Ver
`docs/OptimizationEngine.md` para el flujo real implementado, y esta
sección para el diseño original (conservado como referencia).

## Nota sobre el nombre

El encargo original pide diseñar "GreedyLayerStrategy". Tras comparar
las dos alternativas (sección siguiente), la recomendación técnica es
un enfoque de **extreme points**, no un *layering* estricto. Se
mantiene el nombre de archivo solicitado por continuidad con el
roadmap del producto, pero el identificador técnico interno
(`strategy_name` en `PackingRequest`, `algorithm_name` en
`PackingResult`) debe ser honesto sobre el algoritmo real:
`"greedy_extreme_point_v1"`, no `"greedy_layer_v1"`. Esto separa el
nombre de producto/roadmap del nombre técnico del algoritmo, evitando
que un futuro mantenedor busque un `LayerManager` que nunca existió.

## Objetivo

Colocar el máximo número posible de `PhysicalLoadInstance` en un
`LoadingSpace`, respetando todas las reglas de
`cargo_optimizer.rules`, con un algoritmo simple, correcto,
determinista y fácil de depurar — priorizando corrección sobre
sofisticación en esta primera versión.

## Comparación: Layer-based estricto vs. Extreme-point greedy

### A. Layer-based estricto

Particiona el espacio en capas horizontales por altura; dentro de una
capa, coloca cajas una junto a otra (un problema de *bin packing* 2D
por capa); cuando ninguna caja más cabe a esa altura, abre una capa
nueva encima.

**Ventajas:** modelo mental simple, se parece a cómo un humano suele
pensar "filas" de carga.

**Desventajas:** rígido con cajas de alturas muy distintas — o
desperdicia espacio vertical sobre las cajas más bajas de una capa, o
necesita lógica adicional para rellenar ese hueco con cajas más
pequeñas, que termina pareciéndose a extreme-points de todas formas.
Además, introduce un concepto ("índice de capa") que compite con la
fuente de verdad real que ya calcula el motor de reglas
(`rules.stacking_rules.count_stack_level`, basado en soporte físico
real, no en una capa abstracta) — riesgo genuino de que ambas nociones
diverjan.

### B. Extreme-point greedy con preferencia por menor Z

Mantiene el conjunto de puntos candidatos exactamente como ya los
calcula `geometry.generate_candidate_positions` (origen + esquinas
extremas de cada caja colocada). Por cada instancia, en el orden
decidido (sección siguiente), prueba cada orientación permitida en
cada punto candidato (ordenados por Z, luego X, luego Y), evalúa con
`RulesEngine`, y acepta el candidato mejor puntuado. Tras aceptar,
regenera los puntos candidatos.

**Ventajas:** reutiliza el 100% de lo ya implementado y probado
(`geometry` + `rules`) sin ningún concepto geométrico nuevo; maneja de
forma natural alturas mixtas y apilamiento sin ninguna contabilidad
paralela de "capas"; `count_stack_level` sigue siendo la única fuente
de verdad sobre el nivel de apilamiento.

**Desventajas:** no optimiza explícitamente por "filas" visualmente
ordenadas — puede verse menos ordenado que un layering estricto. Es un
problema estético, no de corrección, y se puede mejorar después
ajustando el *scorer* (p. ej. penalizando variación de altura dentro de
una banda horizontal) sin tocar la lógica de colocación.

### Recomendación

**B (extreme-point greedy).** Prioriza exactamente lo que pide el
encargo: corrección, simplicidad, soporte de apilamiento correcto
(reutilizando lo ya construido), reglas de extintores (sin ningún
ajuste especial: el filtro de orientaciones ya viene resuelto por
`rules.orientation_rules`), extensibilidad (una segunda estrategia
puede introducir *layering* real después, si demuestra mejor calidad,
sin romper el contrato `PackingStrategy`) y calidad razonable para una
primera versión.

## Orden de las instancias

Función pura `default_packing_order_key(instance:
PhysicalLoadInstance) -> tuple`, usada para ordenar
`tuple[PhysicalLoadInstance, ...]` antes de procesarlas:

```python
def default_packing_order_key(instance: PhysicalLoadInstance) -> tuple:
    unit = instance.load_unit
    return (
        0 if is_individual_large_extinguisher(unit) else 1,   # no apilables primero
        0 if unit.fragile else 1,                              # frágiles pronto
        -unit.dimensions.volume_cm3,                            # mayor volumen primero
        -unit.weight_kg,                                        # más pesado primero
        len(unit.allowed_orientation_codes),                    # menos orientaciones primero
        unit.sku,                                               # agrupación estable
        instance.requested_order,                               # desempate final, siempre presente
    )
```

**Justificación de cada criterio, en orden de prioridad:**

1. **Extintores individuales ≥ 3 kg primero**: no pueden recibir nada
   encima (`effective_max_stack_count == 1`). Colocarlos mientras el
   espacio de nivel bajo todavía está libre maximiza sus opciones;
   dejarlos para el final arriesga no encontrarles sitio en absoluto.
2. **Frágiles pronto**: nada puede apoyarse sobre ellos
   (`fragility_rules`). Colocarlos temprano evita que el motor "gaste"
   buenas posiciones de apilamiento esperando poder usarlas encima de
   algo que la regla ya prohíbe.
3. **Mayor volumen primero**: heurística clásica de *decreasing-size*
   en *bin packing* — colocar piezas grandes mientras el espacio está
   vacío reduce fragmentación.
4. **Mayor peso primero**: coherente con estabilidad real de carga
   (más pesado abajo) y con que los límites de peso soportado
   (`max_supported_weight_kg`) son más fáciles de violar cuanto más
   tarde se coloque algo pesado sobre una pila ya cargada.
5. **Menos orientaciones permitidas primero**: heurística de
   "variable más restringida primero" tomada de satisfacción de
   restricciones — un ítem con pocas orientaciones válidas es más
   difícil de encajar más adelante, cuando quede menos espacio libre.
6. **SKU** ascendente: no afecta corrección, solo agrupa
   visualmente ítems del mismo tipo cuando todo lo anterior empata —
   cosmético, determinista.
7. **`requested_order`**: desempate final, siempre presente, garantiza
   un orden total sin ambigüedad bajo cualquier combinación de
   empates.

Las cajas grupales de extintores (1/2/3 kg) no reciben ningún trato
especial más allá de los criterios generales anteriores: no son
"no apilables", así que compiten en la ordenación exactamente como
cualquier otra caja según su volumen, peso y orientaciones.

## Generación de candidatos

Por cada instancia (ya en el orden anterior):

1. Obtener orientaciones permitidas (`allowed_orientations_for_load_unit`,
   con caché por `load_unit.id` — ver `docs/OptimizationEngineDesign.md`,
   sección `OrientationProvider`).
2. Obtener posiciones candidatas (`geometry.generate_candidate_positions(state.placements)`).
3. Para cada orientación (en su orden ya determinista), para cada
   posición (en su orden ya determinista Z/X/Y): construir un
   `CandidatePlacement` provisional.

El orden de recorrido (orientación externa, posición interna, o
viceversa) debe fijarse una vez en la implementación y no cambiar
entre ejecuciones — se recomienda posición externa, orientación
interna (para cada punto candidato, probar primero la orientación
"natural" — código `LWH_XYZ` — antes de rotaciones), porque tiende a
producir resultados más intuitivos visualmente sin afectar la
corrección.

## Selección de orientación

No hay lógica de selección propia de la estrategia más allá de
recorrer la lista ya filtrada y ordenada por `rules`. La estrategia no
decide "qué orientación es mejor" de forma independiente: eso lo
resuelve el *scorer* al comparar candidatos completos
(orientación + posición juntas), no la orientación aislada.

## Score

Ver `docs/OptimizationEngineDesign.md`, sección `CandidateScorer`, para
el diseño completo. Resumen aplicado a Greedy Layer:

```
sort_key = (z_cm, x_cm, y_cm, -support_ratio, generation_index)
```

Se elige el candidato válido (`rule_evaluation.is_allowed`) de menor
`sort_key`. Si ninguno es válido, la instancia queda sin colocar
(`UnpackedReason.NO_FEASIBLE_POSITION`).

## Desempate

Siempre determinista por construcción: `generation_index` (el orden en
que el candidato fue generado, función directa del orden de
orientaciones × posiciones ya fijado) es el último elemento de
`sort_key` y nunca puede empatar entre dos candidatos distintos.

## Relación con `RulesEngine`

La estrategia nunca reimplementa ni una sola regla. Cada candidato pasa
íntegramente por `RulesEngine.evaluate_placement` (a través de
`CandidateEvaluator`), que ya cubre extintores, orientación, límites,
colisión, soporte, apilamiento, fragilidad, peso soportado y peso del
espacio, en ese orden y con la política de no-cascada ya establecida
en la Fase 3 (ADR-0007). La estrategia solo decide *qué* candidatos
generar y *cuál* elegir entre los que ya resultaron válidos.

## Pseudoflujo técnico

```
para cada instancia en orden(instances):
    si cancelado o tiempo agotado o iteraciones agotadas:
        marcar instancias restantes como no colocadas (razón correspondiente)
        romper el bucle
    orientaciones = obtener_orientaciones(instance.load_unit, loading_space)  # con caché
    posiciones = geometry.generate_candidate_positions(state.placements)
    mejor_candidato = None
    indice = 0
    para posicion en posiciones:
        para orientacion en orientaciones:
            evaluacion = evaluar(instance, posicion, orientacion, ...)
            si evaluacion.is_allowed:
                score = puntuar(posicion, orientacion, ..., indice)
                si mejor_candidato es None o score.sort_key < mejor_candidato.score.sort_key:
                    mejor_candidato = CandidatePlacement(..., score)
            indice += 1
    si mejor_candidato is not None:
        placement = mejor_candidato.to_placement(state.next_sequence_number())
        state.accept_placement(placement)
    si no:
        state.reject_instance(instance, NO_FEASIBLE_POSITION, mensaje)
    state.iteration_count += 1
```

## Ejemplos conceptuales

- **Contenedor con 20 cajas idénticas apilables:** las primeras cajas
  ocupan el suelo (nivel 1, soporte completo trivial); a medida que se
  llena la primera "fila" horizontal, los puntos candidatos en Z=0 se
  agotan y el *scorer* empieza a preferir puntos con Z mayor sobre
  cajas ya colocadas — comportamiento de apilamiento emergente, sin
  ningún código de "cambiar de capa".
- **Un extintor individual de 6 kg entre cajas normales:** por el
  orden de instancias, se coloca primero, cuando el suelo aún está
  libre; solo se le ofrecen las 2 orientaciones válidas (eje X); una
  vez colocado, ninguna caja posterior puede aceptarse encima de él
  (`effective_max_stack_count = 1`, verificado por `rules`).
- **Una caja frágil con una caja normal después:** la caja frágil se
  coloca temprano; cualquier candidato posterior que se apoye en ella
  es rechazado por `evaluate_fragility` — el *scorer* nunca llega a
  puntuarlo porque ya es inválido.

## Limitaciones conocidas

- No garantiza una solución óptima (es una heurística voraz, no una
  búsqueda exhaustiva ni con retroceso).
- No reconsidera decisiones pasadas: una vez aceptado un candidato,
  nunca se reubica.
- El resultado puede "verse" menos ordenado que una disposición en
  filas humanas perfectas, aunque sea geométricamente válido.
- Rendimiento O(n³)-ish (ver `docs/OptimizationEngineDesign.md`,
  sección Rendimiento); no apto para decenas de miles de instancias en
  esta versión.
- No distribuye peso por ejes ni considera centro de gravedad
  (explícitamente fuera de alcance de esta fase y de la anterior).

## Criterios de aceptación de la futura Fase 4.1

La implementación se considerará completa cuando:

- exista `src/cargo_optimizer/optimization/` con los componentes
  listados como "Fase 4.1" en la revisión crítica de
  `docs/OptimizationEngineDesign.md`;
- `optimization` dependa únicamente de `domain`, `geometry` y `rules`
  (verificado por `import-linter`);
- dos ejecuciones idénticas produzcan el mismo `PackingResult`
  (prueba de determinismo, mismo patrón que `rules`/`geometry`);
- un extintor individual ≥ 3 kg nunca reciba nada encima en el
  resultado, y siempre quede horizontal con el eje X;
- una caja grupal de extintores de 1/2/3 kg pueda quedar en cualquier
  orientación declarada;
- ninguna colocación del resultado viole ninguna regla de `rules`
  (verificable ejecutando `evaluate_candidate_placement` sobre el
  resultado final);
- exista al menos un escenario de prueba con más instancias de las que
  caben, verificando que las sobrantes aparezcan como `UnpackedUnit`
  con razón coherente, sin excepciones;
- `ruff`, `black`, `mypy --strict`, `import-linter` y `pytest` pasen.
