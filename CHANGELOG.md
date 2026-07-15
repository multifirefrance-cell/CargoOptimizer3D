# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Este proyecto aún no ha alcanzado la versión 1.0; el versionado 0.x
puede incluir cambios estructurales entre versiones menores.

## [0.6.1] - 2026-07-14

Fase 4.2: optimización de rendimiento del motor de packing. Sin
cambios de arquitectura, dominio, `geometry` ni `rules`; sin nueva
dependencia externa; misma API pública y mismo algoritmo
`greedy_extreme_point_v1`.

### Added

- `docs/PerformanceBaseline.md`: metodología, línea base medida (10 y
  100 instancias, escenario mixto realista) y perfilado real con
  `cProfile` antes de optimizar.
- `docs/OptimizerPerformance.md`: resultado real después de optimizar,
  con la conclusión honesta de que **el objetivo obligatorio (5x para
  100 instancias) no se alcanzó** (resultado real: ~1.3x), por qué
  (perfilado real muestra que el 100% del coste restante vive dentro
  de `RulesEngine.evaluate_placement`, fuera del alcance de esta fase),
  y qué alternativas se evaluaron y descartaron (índice espacial,
  precálculo de reglas independientes de posición/orientación).
- `scripts/benchmark_optimizer.py`: benchmark manual reutilizable
  (tamaños configurables, mediana/min/max, conteo de candidatos vía
  modo diagnóstico, memoria pico con `tracemalloc`).
- `src/cargo_optimizer/optimization/pruning.py`:
  `prune_candidate_positions`, poda geométrica segura de puntos
  candidatos (fuera de límites, o estrictamente interiores a una caja
  existente) — nunca poda por heurística de "punto dominado".
- `PackingState.accepted_boxes` y `PackingState.bounding_dimensions`:
  caché incremental, actualizada en O(1) por `accept_placement`.
- `scoring.bounding_volume_increment_from_dimensions`: camino rápido
  que usa dimensiones ya conocidas en vez de recorrer los placements.
- 11 pruebas nuevas: `test_state.py`, `test_pruning.py`,
  `test_regression_greedy_extreme_point.py` (334 pruebas en total en
  la suite automática).

### Changed

- `optimization/candidates.py::build_candidate` ya no recalcula el
  bounding box desde cero por candidato (usa la caché de
  `PackingState`), y solo calcula el *score* (soporte, incremento de
  bounding volume, espacio residual) si la colocación es válida — un
  candidato rechazado nunca se compara por *score*, así que calcularlo
  era trabajo desperdiciado.
- `docs/OptimizationEngine.md`, `docs/Architecture.md`,
  `docs/Roadmap.md`: actualizados con los resultados reales de la fase
  4.2, incluyendo el objetivo no cumplido.

### Fixed

- Ninguna corrección de comportamiento: esta fase es exclusivamente de
  rendimiento. Los resultados (`packed_count`, razones de
  `UnpackedUnit`, determinismo) son idénticos a la fase 4.1,
  verificado por pruebas de regresión dedicadas.

## [0.6.0] - 2026-07-14

### Added

- Primer motor de optimización funcional (fase 4.1):
  `src/cargo_optimizer/optimization/`, hermano de `domain`/`geometry`/
  `rules`, dependiendo únicamente de ellos (verificado con
  `import-linter`, contrato extendido con `optimization` entre
  `application` y `rules`).
- `GreedyExtremePointStrategy` (identificador `greedy_extreme_point_v1`):
  primer algoritmo real de *bin packing* 3D, extreme-point greedy con
  *score* lexicográfico determinista (`z, x, y, -support_ratio,
  incremento de bounding volume, espacio residual aproximado, orden de
  orientación, generation_index`).
- `PackingEngine` (fachada), `PackingRequest`, `PackingProgress`,
  `CancellationToken` — exportados también desde `cargo_optimizer`
  (`from cargo_optimizer import PackingEngine, PackingRequest`).
- `PhysicalLoadInstance`, `expand_load_units`, `order_instances` (9
  criterios: extintor individual grande, orientación única, no
  apilable, volumen, dimensión máxima, peso, SKU, `instance_number`,
  `source_order`).
- `UnpackedReason` (`StrEnum`), jerarquía `OptimizationError` /
  `PackingRequestValidationError` / `OptimizationInternalError`.
- Validación final del layout en `PackingEngine.optimize` antes de
  devolver cualquier resultado; nunca se devuelve un layout
  inconsistente en silencio.
- `docs/OptimizationEngine.md`: documentación de la implementación
  real, incluyendo rendimiento medido (no solo estimado).
- 78 pruebas nuevas: unitarias de `optimization` (69), escenarios de
  extintores realistas, integración de la pila completa
  (`tests/integration/test_packing_engine.py`) y *benchmark* no frágil.
  Total del proyecto: 319 pruebas.

### Fixed

- Las advertencias de `RuleEvaluation` (p. ej. capacidad de extintor
  grupal no estándar) se calculaban pero no llegaban a
  `PackingResult.warnings` en candidatos aceptados; ahora se propagan
  explícitamente.

### Changed

- `docs/OptimizationEngineDesign.md` y
  `docs/GreedyLayerStrategyDesign.md` (diseño de fase 4.0) se
  conservan como historial, con una nota apuntando a
  `docs/OptimizationEngine.md` (implementación real).
- Corrección de expectativas de rendimiento: la estimación de fase 4.0
  ("100 cajas: milisegundos a un par de segundos") resultó muy
  optimista; medido: ~35 s para 100 instancias, crecimiento cúbico. No
  se modificó `rules` ni `geometry` para corregirlo — es el coste ya
  anticipado y pospuesto a v0.7 (poda) / v0.8 (índice espacial).

## [0.5.1] - 2026-07-14

Sesión exclusivamente documental (fase 4.0). Ningún código funcional
cambió; por eso el bump es de versión de parche, no menor, a
diferencia de las fases anteriores que sí modificaron `src/`.

### Added

- `docs/OptimizationEngineDesign.md`: diseño completo del futuro
  `cargo_optimizer.optimization` — responsabilidades, arquitectura,
  15 componentes (`PackingEngine`, `PackingStrategy` como `Protocol`,
  `PackingRequest`, `PackingState`, `PhysicalLoadInstance`,
  `LoadUnitExpander`, evaluador y puntuador de candidatos,
  `PackingResultBuilder`, `UnpackedReason`, entre otros), flujo
  completo, reglas de determinismo, manejo de errores, cancelación y
  progreso sin dependencia de Qt, rendimiento (con evolución v0.6 a
  v0.9), explicabilidad (modo normal/diagnóstico) y revisión crítica.
- `docs/GreedyLayerStrategyDesign.md`: diseño de la primera estrategia
  recomendada (extreme-point greedy, identificador técnico
  `greedy_extreme_point_v1`), orden de instancias, score léxico,
  pseudoflujo y criterios de aceptación de la fase 4.1.
- `docs/ADR/ADR-0008-arquitectura-del-motor-de-optimizacion.md`:
  paquete `optimization` separado, `PackingStrategy` como `Protocol`
  (no `ABC`), determinismo como requisito de diseño.
- `docs/ADR/ADR-0009-estrategia-greedy-y-separacion-objetivos.md`:
  extreme-point greedy frente a *layering* estricto, separación
  estructural entre restricciones duras (de `rules`) y objetivos.

### Changed

- `docs/Architecture.md`, `docs/Roadmap.md`, `CLAUDE.md`: fase 4
  dividida en 4.0 (diseño, completada) y 4.1 (implementación,
  pendiente), siguiendo el mismo patrón ya usado para la fase 2.

## [0.5.0] - 2026-07-14

### Added

- Motor de reglas de negocio (fase 3 del roadmap): paquete
  `cargo_optimizer.rules`, hermano de `domain`/`geometry`, dependiendo
  de `domain` siempre y de `geometry` solo donde una regla necesita
  información espacial (verificado con `import-linter`).
- `RuleSeverity`, `RuleViolation`, `RuleEvaluation` (`allowed`,
  `rejected`, `combine`) como vocabulario común de resultados.
- `PlacementRuleContext` con acceso a la caja candidata, cajas
  existentes y validación de referencias a `LoadUnit` conocidas.
- Reglas de orientación (`allowed_orientations_for_load_unit`,
  `evaluate_orientation`) con deduplicación geométrica.
- Reglas críticas de extintores (`extinguisher_rules.py`): extintores
  individuales >= 3 kg nominales deben ir horizontales con el eje
  `length_cm` paralelo a X; cajas grupales de 1/2/3 kg admiten
  cualquier orientación y capacidades recomendadas (10/8/6) como
  advertencia, no como límite rígido.
- Reglas de apilamiento (`stacking_rules.py`): nivel de apilamiento
  determinista, `effective_max_stack_count`, peso soportado
  transitivo sin doble conteo.
- Reglas de fragilidad, peso del Loading Space y espaciales
  (`fragility_rules.py`, `weight_rules.py`, `spatial_rules.py`),
  reutilizando `cargo_optimizer.geometry` sin duplicar lógica.
- `evaluate_candidate_placement`: evaluación compuesta de 9 pasos con
  política de no-cascada tras colisión (`placement_rules.py`).
- Fachada `RulesEngine` sin estado mutable (`engine.py`).
- `docs/RulesEngine.md` y
  `docs/ADR/ADR-0007-motor-de-reglas.md`.
- 99 pruebas unitarias del motor de reglas (240 en total con dominio y
  geometría).

### Fixed

- `evaluate_supported_weight` ahora recorre toda la cadena transitiva
  de soportes, no solo el soporte directo: si A soporta a B y B
  soporta al candidato, el límite `max_supported_weight_kg` de A
  también se comprueba.

## [0.4.0] - 2026-07-14

### Added

- Motor geométrico determinista (fase 2.2 del roadmap): paquete
  `cargo_optimizer.geometry`, hermano de `domain`, dependiendo
  únicamente de él (verificado con `import-linter`).
- `AxisAlignedBox` con `contains_point`, `contains_box`, `intersects`,
  `overlaps`, `touches` e `intersection_volume_cm3`; `box_from_placement`.
- `fits_inside_loading_space` / `validate_box_inside_loading_space`
  (`geometry/bounds.py`).
- Detección de colisiones O(n²): `boxes_overlap`,
  `placement_overlaps_any`, `find_overlapping_placements`
  (`geometry/collision.py`); tocarse no cuenta como colisión.
- `Rectangle2D` y `union_area_cm2` (unión de rectángulos 2D por
  compresión de coordenadas, sin dependencias externas).
- Soporte físico básico: `support_area_cm2`, `support_ratio`,
  `is_supported`, sin doble conteo de áreas de soporte solapadas.
- `generate_candidate_positions`: puntos candidatos deterministas
  (origen + extremos X/Y/Z de cada Placement), sin heurísticas de
  optimización todavía.
- `validate_layout`: detecta cajas fuera de límites, superposiciones,
  falta de soporte, e `instance_number`/`sequence_number` duplicados.
- `GEOMETRY_EPSILON_CM` (1e-9 cm), tolerancia única centralizada para
  todas las comparaciones geométricas.
- `docs/GeometryEngine.md` y
  `docs/ADR/ADR-0006-motor-geometrico-tolerancia-y-contacto.md`.
- 68 pruebas unitarias del motor geométrico (141 en total con las de
  dominio).

## [0.3.0] - 2026-07-14

### Added

- Modelo de dominio puro (fase 2.1 del roadmap): `Dimensions3D`,
  `Orientation`, `OrientationCode`, `Position3D`, `LoadingSpace` (con
  perfiles orientativos de contenedor 20 ft / 40 ft / 40 ft High
  Cube), `LoadUnit`, `Placement`, `UnpackedUnit`, `PackingResult`,
  `CargoProject` y la jerarquía de excepciones de dominio.
- Enums de dominio con valores string estables (`LoadingSpaceCategory`,
  `DoorPosition`, `PackageType`, `ExtinguisherAgent`,
  `OrientationCode`), heredando de `enum.StrEnum`.
- `docs/DomainModel.md`: sistema de coordenadas, invariantes, diagrama
  Mermaid y distinciones conceptuales (quantity vs. units_per_package
  vs. total_requested_units; peso nominal del extintor vs. peso bruto
  del empaque).
- `docs/ADR/ADR-0005-inmutabilidad-y-enums-estables.md`.
- 73 pruebas unitarias del modelo de dominio.
- `from cargo_optimizer import LoadingSpace, LoadUnit` (y el resto del
  modelo de dominio) disponible como API pública del SDK.

## [0.2.0] - 2026-07-14

### Changed

- Arquitectura reestructurada en capas: `core` → `domain`; `ui` →
  `presentation/desktop`. Se añaden `application` e `infrastructure`
  como capas explícitas, vacías hasta sus fases correspondientes. Ver
  `docs/ADR/ADR-0001-arquitectura-en-capas.md`.

### Added

- `import-linter` como dependencia de desarrollo, con contrato de
  capas que verifica automáticamente la regla de dependencia
  (`presentation → infrastructure → application → domain`).
- `docs/ADR/` con las primeras cuatro decisiones de arquitectura
  registradas.
- `docs/Architecture.md` y `docs/Roadmap.md`.
- `examples/` y `userdata/` (vacíos, con propósito documentado).

## [0.1.0] - 2026-07-14

### Added

- Infraestructura base del repositorio: `pyproject.toml` con Ruff,
  Black, Mypy (modo estricto) y Pytest configurados.
- Paquete `cargo_optimizer` instalable en modo editable, ejecutable
  vía `python -m cargo_optimizer`.
- Aplicación de escritorio mínima con PySide6 (ventana principal).
- Primer test de humo.
