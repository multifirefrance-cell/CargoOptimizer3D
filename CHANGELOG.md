# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Este proyecto aún no ha alcanzado la versión 1.0; el versionado 0.x
puede incluir cambios estructurales entre versiones menores.

## [0.9.0] - 2026-07-15

Implementación mínima funcional del visor 3D (fase 6.1), exactamente
según el diseño aprobado en la fase 6.0 (`docs/ThreeDViewerDesign.md`,
`docs/ThreeDViewerImplementationPlan.md`, ADR-0010, ADR-0011). Cambio
de código real (no documental) — por eso el bump es de versión menor,
mismo criterio que las fases 5.0 y 5.1. `domain`, `geometry`, `rules`
y `optimization` sin ningún cambio (verificado con `git diff` vacío en
los cuatro paquetes antes del commit).

### Added

- Dependencias nuevas: `pyvista>=0.48,<1`, `pyvistaqt>=0.12,<1`,
  `vtk>=9.6,<10` (versiones instaladas confirmadas: pyvista 0.48.4,
  pyvistaqt 0.12.0, vtk 9.6.2, sobre PySide6 6.11.1 / Python 3.12.10).
- `presentation/desktop/viewer/`: `models.py` (`SceneModel`,
  `PlacementVisualModel`), `constants.py` (paleta y colores por tema),
  `color_registry.py` (color por SKU determinista vía `zlib.crc32`,
  nunca `hash()` de Python), `scene_builder.py` (`PackingResult` +
  `load_units_by_id` -> `SceneModel`, función pura sin Qt/VTK),
  `scene_controller.py` (posesión del `Plotter`, construcción de
  `LoadingSpace` y cajas, picking, selección, cámara, temas), `widget.py`
  (`Packing3DViewer(QWidget)`, contrato público completo + fallback
  interno cuando el 3D no está disponible).
- `presentation/desktop/panels/selection_details_panel.py`: panel de
  solo lectura con los datos de la caja seleccionada (SKU, nombre,
  instancia, secuencia de carga, posición, dimensiones orientadas,
  orientación, peso, tipo de empaque, extintor, fragilidad,
  apilamiento, notas).
- Integración completa en `MainWindow`: `Packing3DViewer` sustituye a
  `viewport_3d_placeholder.py` (eliminado) en `work_area_splitter`;
  nuevo `QDockWidget` de detalles de selección en el lado derecho;
  acciones de menú Ver (resetear cámara, mostrar/ocultar espacio de
  carga, cajas, ejes, panel de detalles); el resultado de cada
  optimización se muestra en el visor y una nueva optimización limpia
  la escena anterior; el tema claro/oscuro se propaga al visor.
- `docs/ThreeDViewer.md`: documentación de la implementación real —
  arquitectura, `SceneModel`/`SceneBuilder`/`Packing3DViewer`,
  selección, cámara, temas, fallback, integración, ciclo de vida,
  rendimiento medido (no solo razonado) y limitaciones conocidas,
  incluido el hallazgo de que `pyvistaqt.QtInteractor` provoca un
  segmentation fault nativo de VTK en Windows bajo la plataforma Qt
  `offscreen` (mitigado detectando la plataforma antes de construir el
  interactor, no con un `try/except`).
- 61 pruebas nuevas (`ColorRegistry`, `SceneBuilder`,
  `SceneController` contra un `pyvista.Plotter(off_screen=True)` real,
  `Packing3DViewer` en modo de repuesto bajo `offscreen`,
  `SelectionDetailsPanel`, integración con `MainWindow`).

### Changed

- `docs/ThreeDViewerDesign.md` y `docs/ThreeDViewerImplementationPlan.md`
  marcados como implementados, con nota de las dos desviaciones reales
  (`set_dark_theme(enabled: bool)` en vez de `apply_theme(theme: str)`;
  `focus_placement` implementado en 6.1 en vez de aplazado a 6.2).
- `docs/ADR/ADR-0011-desacoplo-visor-y-fallback.md`: lista de métodos
  no-op del fallback corregida para reflejar los nombres reales.
- `docs/Architecture.md`, `docs/Roadmap.md`, `CLAUDE.md` actualizados
  al estado real de `presentation/desktop/viewer/`.

### Removed

- `presentation/desktop/panels/viewport_3d_placeholder.py`: sustituido
  por `Packing3DViewer`, que incluye su propio contenido de reemplazo
  cuando el 3D no está disponible.

## [0.8.1] - 2026-07-15

Sesión exclusivamente documental (fase 6.0). Ningún código funcional
cambió — por eso el bump es de versión de parche, no menor, mismo
criterio que la fase 4.0 (0.5.0 → 0.5.1). Sin dependencias nuevas
instaladas; `domain`, `geometry`, `rules` y `optimization` sin ningún
cambio (verificado con `git diff` vacío en los cuatro paquetes antes
del commit).

### Added

- `docs/ThreeDViewerDesign.md`: diseño completo del futuro visor 3D —
  evaluación formal de PyVista+PyVistaQt frente a VTK directo,
  `QOpenGLWidget` propio y VisPy; arquitectura de
  `presentation/desktop/viewer/` (seis archivos, no los diez
  originalmente sugeridos, con criterio explícito de cuándo separar
  los tres que se fusionan en 6.1); contrato de `Packing3DViewer`;
  `SceneModel`/`PlacementVisualModel`; cómo `SceneBuilder` resuelve
  SKU/nombre/color de cada `Placement` (mapping `UUID -> LoadUnit`
  entregado junto al resultado, mismo patrón que `UnpackedUnit` desde
  la fase 5.1); sistema de coordenadas (sin permutar ejes); LoadingSpace
  y Placements; colores (determinismo real entre ejecuciones, no con
  `hash()` de Python); cámara; picking y selección con prevención de
  ciclos de señal; filtros dentro/fuera de 6.1; integración con
  `MainWindow`; rendimiento (expectativas razonadas, no medidas);
  temas; captura de imagen y animación futuras; fallback sin 3D
  disponible; riesgos de empaquetado; estrategia de pruebas; decisiones
  descartadas; revisión crítica de 8 preguntas.
- `docs/ThreeDViewerImplementationPlan.md`: reparto en fase 6.1
  (mínimo funcional: dependencia, widget real, LoadingSpace,
  placements, cámara, color por SKU, selección, panel de detalles,
  integración con `MainWindow`, tests), fase 6.2 (filtros, etiquetas,
  modos de color, vistas predefinidas, captura de imagen) y fase 6.3
  (animación, capas, cortes, explosión, optimizaciones de escala).
- `docs/ADR/ADR-0010-tecnologia-del-visor-3d.md`: confirma PyVista +
  PyVistaQt frente a las tres alternativas evaluadas, con riesgos
  aceptados explícitos (empaquetado, renderizado offscreen no
  garantizado, compatibilidad de versiones por confirmar).
- `docs/ADR/ADR-0011-desacoplo-visor-y-fallback.md`: API del visor
  basada en `PackingResult` ya calculado (nunca ejecuta el motor);
  fallback informativo cuando 3D no está disponible, con todos los
  métodos públicos convertidos en no-op seguros.

### Changed

- `docs/Architecture.md`: añadida la estructura diseñada (no creada)
  de `presentation/desktop/viewer/`, hermana de `panels/`/`models/`/
  `workers/`.
- `docs/Roadmap.md`: corrige la fila original de la fase 6 (decía
  "`infrastructure` (adaptador VTK)"; el visor pertenece a
  `presentation/desktop/viewer/`, no a `infrastructure`) y la subdivide
  en 6.0 (diseño, completada), 6.1/6.2/6.3 (implementación, pendientes)
  — mismo criterio que las fases 2, 4 y 5.
- `CLAUDE.md`: nueva sección de invariantes para el futuro
  `presentation/desktop/viewer/` (desacoplo del motor, fallback,
  determinismo de color, no permutar ejes).

## [0.8.0] - 2026-07-15

Fase 5.1: conecta la interfaz de escritorio de la fase 5.0 con el
motor real. Trabajo exclusivamente dentro de `presentation/desktop`;
`domain`, `geometry`, `rules` y `optimization` quedan sin ningún
cambio (verificado con `git diff` vacío en los cuatro paquetes antes
del commit) — esta fase solo consume la API pública del motor.

### Added

- `presentation/desktop/workers/optimization_worker.py`:
  `OptimizationWorker(QThread)`, el único módulo de la interfaz que
  importa `PackingEngine`/`CancellationToken`. Ejecuta
  `PackingEngine.optimize(...)` en un hilo dedicado (nunca en el hilo
  de la GUI), con señales `progress`/`optimization_finished`/
  `optimization_failed` que entregan `PackingProgress`/`PackingResult`/
  el mensaje de error al hilo principal vía conexión en cola.
- `MainWindow._build_packing_request()`: lee `LoadingSpace` del
  formulario y `LoadUnit` de la tabla de productos, construye una
  `PackingRequest` real y explica con `QMessageBox.warning` — sin
  ejecutar nada — si falta un espacio válido, no hay productos, o la
  solicitud es inválida (p. ej. SKU duplicados tras editar la tabla).
- "Ejecutar optimización" ahora deshabilita los controles relevantes
  (tabla de productos, formulario de espacio, nuevo/abrir/importar),
  lanza `OptimizationWorker`, y los rehabilita automáticamente al
  terminar (éxito, cancelación o error), vía la señal `QThread.finished`
  como único punto de limpieza.
- "Cancelar" activa el `CancellationToken` cooperativo del worker en
  curso; la interfaz espera su finalización limpia de forma asíncrona
  (nunca bloqueando la GUI con `QThread.wait()`, salvo al cerrar la
  ventana) y queda consistente en cuanto el hilo termina.
- Barra de progreso y tiempo transcurrido en la `StatusBar`, alimentados
  por `PackingProgress`; `StatusBar` ahora también refleja el estado
  real de la ejecución (listo/preparando/optimizando/cancelando/
  finalizado/error).
- El panel inferior pasa a ser un `QTabWidget` con cuatro pestañas:
  - **Resumen** (`ResultsPanel`, ampliado): cantidad solicitada/
    cargada/pendiente, peso, volumen, utilización, tiempo, estado y
    conteo de avisos — poblado automáticamente desde `PackingResult`.
  - **No cargados** (`UnpackedTablePanel` + `UnpackedUnitTableModel`,
    nuevos): SKU, instancia, razón y código de cada `UnpackedUnit` real.
  - **Avisos** (`WarningsPanel`, nuevo): `PackingResult.warnings` tal
    cual, sin reinterpretarlos por origen (el propio motor ya los
    agrega en un único conjunto — ver `docs/OptimizationEngine.md`).
  - **Registro** (`LogPanel`, nuevo): inicio, fin, duración,
    cancelación y errores de cada ejecución, con marca de tiempo.
- `tests/presentation/desktop/`: 16 pruebas nuevas —
  `test_optimization_worker.py` (ejecución síncrona determinista,
  cancelación pre-armada sin condición de carrera, fallo del motor,
  y una prueba con `.start()` real que verifica que no bloquea al
  llamador), `test_unpacked_table_model.py`, y
  `test_main_window_optimization.py` (construcción de solicitud,
  validaciones, ejecución de punta a punta, cancelación, error vía
  `QMessageBox`, resultados/avisos/pendientes). 386 pruebas en total.

### Changed

- `docs/Architecture.md`, `docs/Roadmap.md`: fase 5.1 marcada
  completada, fase 6 (visualización 3D) como siguiente paso.
- `CLAUDE.md`: nuevas invariantes de `presentation/desktop` para el
  ciclo de vida del worker y la regla de "todo error por QMessageBox,
  nunca solo por consola".

### Fixed

- Ninguna corrección de comportamiento del motor: esta fase es
  exclusivamente de integración de interfaz.

## [0.7.0] - 2026-07-15

Fase 5.0: base profesional de la interfaz de escritorio. Trabajo
exclusivamente dentro de `presentation/desktop`; el motor
(`domain`/`geometry`/`rules`/`optimization`) queda congelado y no se
invoca todavía desde la interfaz.

### Added

- `MainWindow` real: `QMainWindow` con `QSplitter` anidados (panel de
  trabajo + panel de resultados; formulario + tabla de productos +
  vista 3D) y un `QDockWidget` para el árbol de proyecto. 8 menús
  (Archivo, Proyecto, Espacio de carga, Productos, Optimización, Ver,
  Herramientas, Ayuda) con acciones reales o, cuando el motor todavía
  no aplica, un mensaje explícito "disponible en una próxima versión"
  en la barra de estado — nunca una acción vacía. Toolbar con los 8
  botones pedidos (Nuevo, Abrir, Guardar, Importar, Optimizar,
  Cancelar, Vista 3D, Preferencias).
- `panels/project_tree_panel.py`: árbol de secciones del proyecto
  (Espacios, Productos, Resultados, Configuración).
- `panels/loading_space_form_panel.py`: formulario del Loading Space
  con perfiles predefinidos (20'/40'/40HQ vía
  `LoadingSpace.standard_*_container()`, más camión/semirremolque/
  furgón/van/bodega/otro definidos en esta capa) y modo
  "Personalizado" que desbloquea la edición libre de todos los campos.
- `models/product_table_model.py`: `ProductTableModel`
  (`QAbstractTableModel`, no `QTableWidget`) sobre una lista de
  `LoadUnit` reales, con las 14 columnas pedidas y edición preparada
  (`setData` reconstruye el `LoadUnit` inmutable vía
  `dataclasses.replace`, rechazando la edición si el dominio la
  invalida). `panels/product_table_panel.py` la envuelve en un
  `QTableView` con altas/bajas de filas mínimas.
- `panels/results_panel.py`: resumen inferior (cantidad solicitada/
  cargada, peso, volumen, utilización, tiempo, estado), con la forma
  final que usará la fase 5.1 pero valores vacíos por ahora.
- `panels/viewport_3d_placeholder.py`: placeholder elegante de la
  vista 3D ("Vista 3D disponible en la Fase 6"), sin VTK.
- `style.py`: paletas claro y oscuro completas (no solo la clara con
  una promesa de oscuro futuro) más una hoja de estilos mínima de
  aspecto industrial; alternables desde el menú Ver.
- `icons.py` + `resources/icons/*.svg`: 8 iconos SVG monocromos
  propios (nuevo, abrir, guardar, importar, optimizar, cancelar, vista
  3D, preferencias).
- `settings.py`: `AppSettings`, wrapper de `QSettings` con claves
  centralizadas — geometría/estado de `MainWindow`, estado de los tres
  `QSplitter`, anchos de columna de la tabla de productos, último
  directorio usado y último perfil de Loading Space. Sin SQLite.
- `tests/presentation/desktop/`: 36 pruebas nuevas (creación de
  `MainWindow`, menús/toolbar/status bar, modelo de productos, carga y
  bloqueo de perfiles del formulario de espacio, árbol de proyecto,
  persistencia de `AppSettings`), todas bajo la plataforma Qt
  `offscreen` para no depender de un entorno gráfico. 370 pruebas en
  total.

### Fixed

- `cargo_optimizer.__version__` seguía en `"0.6.0"` mientras
  `pyproject.toml` ya declaraba `"0.6.1"` desde la fase 4.2 (bug
  objetivo y demostrable, no relacionado con el motor): ambos quedan
  sincronizados en `"0.7.0"`.

### Changed

- `docs/Roadmap.md`: la fase 5 se renumera de "5 = Visualización 3D, 6
  = Interfaz" a "5.0/5.1 = Interfaz, 6 = Visualización 3D" (ver la nota
  dedicada en ese documento) para reflejar el orden realmente
  construido.
- No se conecta `PackingEngine` desde la interfaz todavía (fase 5.1);
  no se implementa VTK, SQLite, Excel, PDF, importación/exportación
  real, animaciones ni Undo/Redo — todo deliberadamente fuera de
  alcance de esta fase.

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
