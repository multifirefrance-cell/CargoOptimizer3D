# ADR-0009: Extreme-point greedy como primera estrategia; separación entre restricciones duras y objetivos

## Estado

Aceptada — 2026-07-14

## Contexto

El encargo original nombra a la primera estrategia
"GreedyLayerStrategy" y pide comparar un enfoque de *layering* estricto
contra uno de *extreme points*. También pide distinguir claramente
restricciones duras de objetivos de optimización, sin mezclarlas en un
único sistema de puntuación.

## Decisión 1: la primera estrategia es extreme-point greedy, no layering estricto

Comparación completa en `docs/GreedyLayerStrategyDesign.md`. Resumen:
el *layering* estricto introduce un concepto nuevo ("índice de capa")
que puede divergir de la fuente de verdad real que ya calcula
`rules.stacking_rules.count_stack_level` (basada en soporte físico
real, no en una capa abstracta), y maneja peor alturas mixtas sin
lógica adicional que termina pareciéndose a extreme-points de todas
formas. Extreme-point greedy reutiliza el 100% de
`geometry.generate_candidate_positions` y `rules.evaluate_candidate_placement`
ya implementados y probados, sin ningún concepto geométrico nuevo.

Se mantiene el nombre de archivo `GreedyLayerStrategyDesign.md` y el
nombre de producto/roadmap por continuidad, pero el identificador
técnico (`strategy_name`/`algorithm_name`) será
`"greedy_extreme_point_v1"`, honesto sobre el algoritmo real, para que
un futuro mantenedor no busque un `LayerManager` que nunca existió.

## Decisión 2: restricciones duras y objetivos nunca se mezclan en un único score

**Restricciones duras** (binarias, ya implementadas en `rules`):
límites, colisión, soporte, orientación (incluida la regla de
extintores), apilamiento, fragilidad, peso soportado, peso máximo del
espacio. Un candidato que viola cualquiera de ellas es inválido, punto
— nunca se pondera ni se "compensa" con un buen score en otro criterio.

**Objetivos** (graduales, deciden cuál candidato *válido* es mejor):
para v1, un único objetivo claro — maximizar la cantidad de instancias
cargadas — apoyado por un *score* lexicográfico local (menor Z, luego
X, luego Y, mayor soporte, desempate por orden de generación) que guía
la elección voraz hacia soluciones densas, sin ser en sí mismo un
objetivo independiente que compita con "cargar más cajas". Se
descarta explícitamente una suma ponderada de objetivos
(`objective_weights`) para v1: exige calibrar constantes arbitrarias
entre magnitudes no comparables, dificulta explicar por qué un
candidato ganó, y puede reordenar resultados de forma silenciosa ante
pequeños ajustes numéricos. Un orden lexicográfico no requiere
calibración y es trivialmente explicable.

Objetivos como "minimizar huecos", "distribuir peso" o "facilitar
descarga" quedan explícitamente pospuestos a fases posteriores; v1 no
promete optimizarlos, solo no los empeora activamente por diseño (el
greedy con preferencia de menor Z tiende, como efecto secundario, a
producir capas razonablemente densas).

## Consecuencias

**Beneficios:**
- Ninguna violación de regla puede "colarse" por tener buen score en
  otro criterio — la separación es estructural (un candidato inválido
  ni siquiera se puntúa), no solo una convención de código.
- El resultado de v1 es completamente explicable sin necesitar
  justificar pesos arbitrarios.
- Cambiar de estrategia en el futuro (p. ej. `BeamSearchStrategy` con
  múltiples objetivos ponderados) no exige revisar cómo se definieron
  las restricciones duras: siguen siendo las mismas de `rules`.

**Costes / riesgos aceptados:**
- v1 no intenta activamente minimizar huecos ni distribuir peso; la
  calidad de la solución más allá de "cantidad cargada" queda como
  trabajo futuro explícito, documentado, no resuelto por accidente.
- El nombre de archivo (`GreedyLayerStrategyDesign.md`) no coincide
  literalmente con el algoritmo recomendado dentro de él; se acepta
  porque el propio documento lo aclara en su primera sección y el
  identificador técnico (`strategy_name`) sí es preciso.
