# Motor de optimización: implementación real (Fases 4.1-4.2)

Este documento describe lo que **realmente existe** en
`src/cargo_optimizer/optimization/`, a diferencia de
`docs/OptimizationEngineDesign.md` y
`docs/GreedyLayerStrategyDesign.md` (fase 4.0), que describían el
diseño antes de implementarlo. Donde la implementación difiere del
diseño, se indica explícitamente. La fase 4.2 (optimización de
rendimiento) añadió caché incremental de bounding box y poda segura de
candidatos sin cambiar el algoritmo ni la API pública — ver
`docs/OptimizerPerformance.md` para el detalle completo, incluyendo por
qué el objetivo de rendimiento de esa fase no se alcanzó del todo.

## Componentes implementados

| Módulo | Contenido |
|---|---|
| `exceptions.py` | `OptimizationError`, `PackingRequestValidationError`, `OptimizationInternalError` |
| `codes.py` | `UnpackedReason` (`StrEnum`) |
| `models.py` | `PackingRequest`, `PhysicalLoadInstance`, `PackingProgress`, `CandidatePlacement` (todos inmutables) |
| `state.py` | `PackingState` (mutable, interno, nunca público); cachea incrementalmente `accepted_boxes` y `bounding_dimensions` (fase 4.2) |
| `cancellation.py` | `CancellationToken` (basado en `threading.Event`) |
| `expander.py` | `expand_load_units` |
| `ordering.py` | `order_instances` |
| `scoring.py` | `bounding_dimensions`, `bounding_volume_cm3`, `bounding_volume_increment_cm3` (recorre placements, uso puntual), `bounding_volume_increment_from_dimensions` (camino rápido, fase 4.2), `local_residual_space_cm3`, `score_candidate` |
| `candidates.py` | `orientation_fits_loading_space`, `build_candidate` (solo calcula *score* si el candidato es válido, fase 4.2) |
| `pruning.py` | `prune_candidate_positions` (poda segura de puntos candidatos, fase 4.2) |
| `result_builder.py` | `build_packing_result` |
| `strategy.py` | `PackingStrategy` (Protocol), `StrategyCapabilities` |
| `greedy_extreme_point.py` | `GreedyExtremePointStrategy` (identificador `greedy_extreme_point_v1`) |
| `engine.py` | `PackingEngine` (fachada pública) |

Todos dependen únicamente de `domain`, `geometry` y `rules` — verificado
por `import-linter` (contrato `layers` extendido con `optimization`
entre `application` y `rules`).

## Flujo real

`PackingEngine.optimize(request, cancellation_token=None,
progress_callback=None)`:

1. Crea un `RulesEngine()` y un `CancellationToken()` propio si no se
   proporciona uno.
2. Delega en `strategy.pack(request, rules_engine, token, callback)`
   (por defecto, `GreedyExtremePointStrategy`).
3. Ejecuta `geometry.layout_validation.validate_layout` sobre el
   resultado de la estrategia como verificación final de coherencia.
   Si `request.minimum_support_ratio >= 1.0`, exige soporte completo en
   esa validación; si el usuario pidió un ratio menor, la validación
   final no contradice esa decisión explícita (ver "Validación final").
4. Si el layout es válido, devuelve el `PackingResult` tal cual. Si no,
   lanza `OptimizationInternalError` — nunca devuelve un layout
   inconsistente en silencio.

Dentro de `GreedyExtremePointStrategy.pack(...)`:

1. Construye `load_units_by_id`.
2. `expand_load_units(request.load_units)` → instancias físicas.
3. `order_instances(...)` → orden determinista (ver más abajo).
4. Crea un `PackingState` vacío y un caché de orientaciones por
   `load_unit.id` (evita recalcular `RulesEngine.allowed_orientations`
   para cada instancia de un mismo `LoadUnit` con `quantity` alta).
5. Emite el progreso inicial.
6. Para cada instancia, en orden:
   - comprueba cancelación, límite de tiempo y límite de iteraciones;
     si se activa alguno, detiene el bucle (no es un error);
   - obtiene orientaciones (con caché) y las filtra con
     `orientation_fits_loading_space` (descarta las que no caben ni
     desde el origen, sin evaluar reglas);
   - genera posiciones candidatas con
     `geometry.generate_candidate_positions(state.placements)`;
   - construye y evalúa cada candidato (`build_candidate`, que delega
     en `RulesEngine.evaluate_placement`);
   - entre los candidatos válidos, elige el de menor `score`;
   - si hay elegido: `state.accept_placement(...)` y propaga a
     `state.warnings` cualquier advertencia (`RuleSeverity.WARNING`)
     de la evaluación aceptada (p. ej. capacidad de extintor grupal no
     estándar — ver "Corrección aplicada durante esta fase");
   - si no hay ninguno válido: clasifica la causa (ver más abajo) y
     registra un `UnpackedUnit`.
7. Si el bucle se detuvo por cancelación/tiempo/iteraciones, marca
   todas las instancias restantes con la razón correspondiente y añade
   una advertencia explicando cuántas quedaron sin procesar.
8. Emite el progreso final y construye el `PackingResult`
   (`build_packing_result`).

## Corrección aplicada durante esta fase

Al escribir los tests del escenario F ("capacidad grupal
personalizada: warning, no rechazo") se detectó que las advertencias
de `RuleEvaluation` (p. ej. `EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD`)
se calculaban correctamente pero nunca llegaban a
`PackingResult.warnings`: se descartaban en silencio al aceptar el
candidato. Se corrigió propagándolas explícitamente en
`GreedyExtremePointStrategy._process_instance` justo tras
`state.accept_placement(...)`. No es un cambio de diseño (ya estaba
previsto que las advertencias de reglas fueran visibles), sino una
omisión de la primera versión del bucle principal.

## Score

Implementado exactamente como en el diseño (ver ADR-0009):

```
score = (z, x, y, -support_ratio, incremento_bounding_volume, espacio_residual_aprox, orden_orientacion, generation_index)
```

Comparado lexicográficamente (tuplas de Python), nunca con suma
ponderada. `generation_index` es siempre el desempate final.

## Orden de instancias

`order_instances` implementa exactamente los 9 criterios pedidos, en
este orden de prioridad: extintor individual grande primero,
orientación única primero, no apilable primero, mayor volumen, mayor
dimensión máxima, mayor peso, SKU, `instance_number`, `source_order`.
`orientation_count` y `effective_max_stack_count` se cachean por
`load_unit.id` dentro de la llamada (evita recalcular para cada
instancia repetida del mismo `LoadUnit`).

## Determinismo

Verificado con pruebas (`test_determinism` en `test_ordering.py`,
`test_scoring.py`, `test_packing_scenarios.py` y
`test_packing_engine.py`): la misma solicitud, ejecutada varias veces,
produce exactamente los mismos `placements`, `unpacked_units` y
`warnings`. El único campo que difiere entre ejecuciones idénticas es
`execution_time_seconds` (un reloj de pared, nunca parte de la
comparación de determinismo).

## Razones de unpacked

`UnpackedReason` (no duplica los códigos de `rules.codes`, que son más
finos): `NO_VALID_ORIENTATION`, `NO_FEASIBLE_POSITION`,
`LOADING_SPACE_WEIGHT_EXCEEDED`, `TIME_LIMIT_REACHED`,
`ITERATION_LIMIT_REACHED`, `CANCELLED`, `INVALID_INPUT`,
`INTERNAL_VALIDATION_FAILED`.

Clasificación real cuando ninguna posición/orientación es válida: se
acumula el conjunto de todos los códigos de violación vistos en los
candidatos rechazados de esa instancia. Si el conjunto es exactamente
`{LOADING_SPACE_WEIGHT_EXCEEDED}`, la causa es esa; si no hay ninguna
orientación que quepa ni desde el origen, `NO_VALID_ORIENTATION`; en
cualquier otro caso, `NO_FEASIBLE_POSITION`. En la práctica, el caso
"solo por peso" únicamente es alcanzable de forma limpia cuando la
instancia no tiene ningún placement previo con el que competir por el
origen (ver comentario en
`tests/optimization/test_packing_scenarios.py::test_loading_space_weight_limit_is_respected`):
en cuanto existe al menos una colocación previa, el candidato en el
origen siempre colisiona con ella, añadiendo `COLLISION` al conjunto y
haciendo que la clasificación general (`NO_FEASIBLE_POSITION`)
predomine — comportamiento correcto, no un defecto.

## Límites de ejecución y resultados parciales

`time_limit_seconds`, `max_iterations` y `CancellationToken` se
comprueban al principio de cada iteración del bucle principal. Cuando
se activa cualquiera, las instancias ya colocadas se conservan tal
cual, las pendientes se marcan como `UnpackedUnit` con la razón
correspondiente, y se añade una advertencia. Nunca se lanza una
excepción por esto: el `PackingResult` parcial es un resultado normal.

## Cancelación y progreso

`CancellationToken` (basado en `threading.Event`) permite cancelar
desde otro hilo sin corromper `PackingState` (la cancelación solo
detiene el inicio de la siguiente instancia, nunca interrumpe una
mutación a mitad). `PackingProgress` se emite al inicio, tras cada
instancia procesada y al final. **Una excepción lanzada por el
callback de progreso se convierte en una advertencia
(`PackingResult.warnings`) y la ejecución continúa con normalidad** —
decisión explícita, documentada aquí y verificada por
`test_progress_callback_error_is_converted_to_warning`.

## Validación final

`PackingEngine` ejecuta `geometry.validate_layout` sobre el resultado
antes de devolverlo. Si `request.minimum_support_ratio` es 1.0 (el
valor por defecto), exige soporte completo en esa comprobación. Si el
usuario pidió explícitamente un ratio menor, la validación final no
puede exigir soporte completo (contradiría lo que el propio motor
aceptó intencionadamente al empaquetar): límites, colisiones y
duplicados sí se comprueban siempre, porque ninguna colocación
aceptada debería violarlos jamás, sea cual sea el ratio de soporte
solicitado. Si la validación falla, se lanza
`OptimizationInternalError` — indica un bug real del motor, nunca se
oculta.

## Complejidad y rendimiento (medido, no estimado)

**Corrección sobre `docs/OptimizationEngineDesign.md`:** el diseño de
fase 4.0 estimaba, antes de medir, "100 cajas: milisegundos a un par
de segundos". La medición real (fase 4.1, antes de optimizar) fue
sustancialmente más lenta: ~0.2 s para 10 instancias, ~103 s para 100
(escenario mixto realista), del orden de 41 minutos para 500
(`docs/PerformanceBaseline.md`).

La fase 4.2 aplicó las optimizaciones seguras posibles dentro de
`optimization` (caché incremental de bounding box, omisión de *score*
para candidatos rechazados, poda geométrica de puntos candidatos — ver
`docs/OptimizerPerformance.md`), con resultado real de **~1.3x** para
10 y 100 instancias — muy por debajo del objetivo obligatorio de 5x
que se había fijado para esa fase. El perfilado real (`cProfile`,
repetido después de optimizar) muestra que el 100% del tiempo restante
vive dentro de `RulesEngine.evaluate_placement`
(`find_direct_supporting_placements`, `evaluate_collision`,
`evaluate_supported_weight`), no en el código propio de
`optimization`, que quedó con coste propio prácticamente nulo. El
crecimiento observado sigue siendo marcadamente peor que lineal: cada
candidato evaluado recorre `O(instancias ya colocadas)` dentro de
`RulesEngine`, y el número de candidatos por instancia también crece
con el layout — el producto es cúbico. Esto **no es un bug de `rules`
ni de `geometry`**: es un diseño ya documentado de la fase 3, y
reducirlo de raíz requeriría una estructura de datos espacial dentro
de `rules`/`geometry` mismos, fuera del alcance autorizado de la fase
4.2 (ver `docs/OptimizerPerformance.md`, sección "Conclusión
honesta").

**Consecuencia práctica para la suite de pruebas:** el benchmark
automático (`tests/optimization/test_performance.py`) solo cubre
10/30/60 instancias (segundos en total). 100 y 500 se documentan aquí
como medición manual, no como parte de la suite normal — incluir 500
en la suite automática la haría tardar decenas de minutos.

## Ejemplo de uso

```python
from cargo_optimizer import PackingEngine, PackingRequest
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace

space = LoadingSpace(
    name="Camión de reparto",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(420.0, 210.0, 220.0),
    max_weight_kg=1500.0,
)
unit = LoadUnit(
    sku="BOX-1", name="Caja", dimensions=Dimensions3D(50.0, 40.0, 30.0),
    weight_kg=15.0, quantity=20,
)
request = PackingRequest(loading_space=space, load_units=(unit,))

result = PackingEngine().optimize(request)
print(result.packed_count, "/", result.requested_count, "colocadas")
for unpacked in result.unpacked_units:
    print(unpacked.reason_code, unpacked.reason_message)
```

## Limitaciones actuales

- Rendimiento O(n³)-ish real (medido más arriba), incluso tras la
  optimización de la fase 4.2; no apto para cientos de instancias en
  tiempo interactivo con esta primera versión. Reducirlo de raíz
  requeriría tocar `rules`/`geometry` (ver `docs/OptimizerPerformance.md`).
- Una sola estrategia (`greedy_extreme_point_v1`); sin registro
  dinámico ni plugins.
- Un único `LoadingSpace` por ejecución.
- Sin distribución de peso por ejes ni centro de gravedad avanzado.
- El modo diagnóstico completo (traza de todos los candidatos
  intentados) no está implementado; solo se conserva la causa
  clasificada y los avisos generales.
