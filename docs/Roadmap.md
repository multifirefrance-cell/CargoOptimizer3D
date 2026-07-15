# Roadmap de CargoOptimizer3D

Cada fase se diseña y documenta antes de escribir código (ver
`CLAUDE.md`, sección "Reglas de trabajo con el asistente"). Ninguna
fase se adelanta a la anterior.

| Fase | Nombre | Paquete(s) que crea o rellena | Estado |
|---|---|---|---|
| 0 | Diseño completo | — | Completada |
| 1 | Arquitectura | `domain`, `application`, `infrastructure`, `presentation` (estructura, vacíos donde aplique) | **Completada** |
| 2.1 | Modelo de dominio puro | `domain` (entidades y value objects: `Dimensions3D`, `Orientation`, `LoadingSpace`, `LoadUnit`, `Position3D`, `Placement`, `UnpackedUnit`, `PackingResult`, `CargoProject`) | **Completada** |
| 2.2 | Motor geométrico (geometría, colisiones, soporte) | `geometry` (hermano de `domain`) | **Completada** |
| 3 | Motor de restricciones | `rules` (hermano de `domain`) | **Completada** |
| 4.0 | Diseño del motor de optimización | Ninguno (solo documentación: `docs/OptimizationEngineDesign.md`, `docs/GreedyLayerStrategyDesign.md`, ADR-0008, ADR-0009) | **Completada** |
| 4.1 | Primer optimizador funcional | `optimization` (hermano de `domain`) | **Completada** |
| 4.2 | Optimización de rendimiento del motor de packing | `optimization` (mismos módulos, sin nuevo paquete) | **Completada** |
| 5 | Visualización 3D | `infrastructure` (adaptador VTK) | Pendiente |
| 6 | Interfaz | `presentation/desktop` (pantallas reales) | Pendiente |
| 7 | Persistencia | `infrastructure` (adaptador SQLAlchemy/SQLite) | Pendiente |
| 8 | Reportes | `infrastructure` (adaptadores openpyxl/ReportLab) | Pendiente |
| 9 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 10 | Versión comercial | — | Pendiente |

## `optimization` (`geometry`, `rules` y `optimization` ya existen)

`geometry` se creó en la fase 2.2 (ver `docs/GeometryEngine.md` y
ADR-0006). `rules` se creó en la fase 3 (ver `docs/RulesEngine.md` y
ADR-0007). `optimization` se diseñó en la fase 4.0
(`docs/OptimizationEngineDesign.md`, `docs/GreedyLayerStrategyDesign.md`,
ADR-0008, ADR-0009) y se implementó en la fase 4.1
(`docs/OptimizationEngine.md`): depende únicamente de `domain`,
`geometry` y `rules`, reflejado en el contrato de `import-linter`
(`optimization` entre `application` y `rules`). Contiene la estrategia
`greedy_extreme_point_v1` (`GreedyExtremePointStrategy`) y la fachada
`PackingEngine`, ya exportada desde `cargo_optimizer` (`from
cargo_optimizer import PackingEngine, PackingRequest`).

## Regla para crear adaptadores de `infrastructure` y `presentation`

- Un adaptador de `infrastructure` (SQLite, Excel, PDF, VTK) se crea
  como subpaquete de `infrastructure` en la fase que lo introduce
  (p. ej. `infrastructure/persistence/`, `infrastructure/reporting/`).
- Un nuevo mecanismo de entrega (API REST, web) se crea como subpaquete
  hermano de `presentation/desktop`, p. ej. `presentation/api/`, sin
  modificar el código de escritorio existente.

## Nota sobre la numeración de la fase 2

La fase 2 original ("Motor geométrico") se dividió en dos entregas:
**2.1 Modelo de dominio puro** (completada en esta sesión) y **2.2
Motor geométrico** (colisiones, packing — pendiente). Se optó por esta
subdivisión, en vez de renumerar en cascada las fases 3-10 ya
documentadas en `CLAUDE.md` y `docs/Architecture.md`, para no romper
referencias existentes por un ajuste que es de alcance, no de
arquitectura.

## Estado actual

Fin de fase 4.2: optimización de rendimiento del motor de packing
(`GreedyExtremePointStrategy`, identificador `greedy_extreme_point_v1`
sin cambios, misma API pública `from cargo_optimizer import
PackingEngine, PackingRequest`). Se aplicaron tres optimizaciones
seguras dentro de `optimization` (caché incremental de bounding box en
`PackingState`, omisión del *score* para candidatos rechazados, poda
geométrica de puntos candidatos en `pruning.py`), verificadas con 334
pruebas en verde (suite automática completa, sin contar el benchmark
manual de 500 instancias) y perfilado real con
`cProfile` antes y después. **El objetivo obligatorio de esta fase (5x
más rápido para 100 instancias) no se alcanzó**: el resultado real es
~1.3x, porque el perfilado muestra que, tras optimizar, el 100% del
tiempo restante vive dentro de `RulesEngine.evaluate_placement`
(soporte, apilamiento, peso soportado, colisión), fuera del alcance
autorizado de esta fase. Detalle completo, con las alternativas
evaluadas y descartadas (índice espacial, precálculo de reglas
independientes de posición), en `docs/OptimizerPerformance.md`. No se
ha escrito código de visualización 3D, persistencia, exportación ni
API. La siguiente sesión de desarrollo debe elegir entre: (a) el diseño
de la fase 5 (visualización 3D), o (b) — si el rendimiento a gran
escala (250+ instancias) sigue siendo prioritario — una fase nueva,
con ADR explícito, para introducir una estructura de datos espacial
**dentro de `rules`/`geometry`** (no solo en `optimization`), única vía
identificada para reducir el coste dominante real.
