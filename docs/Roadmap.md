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
| 4.1 | Primer optimizador funcional | `optimization` (nuevo, hermano de `domain`); primer caso de uso real en `application` | Pendiente |
| 5 | Visualización 3D | `infrastructure` (adaptador VTK) | Pendiente |
| 6 | Interfaz | `presentation/desktop` (pantallas reales) | Pendiente |
| 7 | Persistencia | `infrastructure` (adaptador SQLAlchemy/SQLite) | Pendiente |
| 8 | Reportes | `infrastructure` (adaptadores openpyxl/ReportLab) | Pendiente |
| 9 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 10 | Versión comercial | — | Pendiente |

## Regla para crear `optimization` (`geometry` y `rules` ya existen; `optimization` ya está diseñado)

`geometry` se creó en la fase 2.2 (ver `docs/GeometryEngine.md` y
ADR-0006). `rules` se creó en la fase 3 (ver `docs/RulesEngine.md` y
ADR-0007). `optimization` se **diseñó** en la fase 4.0 (ver
`docs/OptimizationEngineDesign.md`, `docs/GreedyLayerStrategyDesign.md`,
ADR-0008, ADR-0009) pero **no se crea como paquete de código hasta la
fase 4.1**. Al crearse, debe:

1. Depender únicamente de `domain`, `geometry` y `rules` (nunca de
   `application`, `infrastructure` ni `presentation`).
2. Quedar reflejado en el contrato de `import-linter` en
   `pyproject.toml`, insertando `optimization` entre `application` y
   `rules`.
3. Implementar únicamente lo listado como "Fase 4.1" en la revisión
   crítica de `docs/OptimizationEngineDesign.md` — no más, no menos.

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

Fin de fase 4.0: diseño completo del motor de optimización
(`PackingEngine`, `PackingStrategy` como `Protocol`,
`PackingRequest`/`PackingState`, expansión de instancias físicas,
evaluación y puntuación de candidatos, manejo de errores,
cancelación/progreso, rendimiento y explicabilidad), con la primera
estrategia recomendada (extreme-point greedy,
`greedy_extreme_point_v1`) documentada en detalle. Sigue habiendo 240
pruebas unitarias en verde (73 de dominio + 68 de geometría + 99 de
reglas): esta fase no añadió código funcional, solo documentación y
dos ADR. No se ha escrito ninguna línea de algoritmo de packing. La
siguiente sesión de desarrollo debe implementar la fase 4.1 (primer
optimizador funcional) siguiendo exactamente lo diseñado en
`docs/OptimizationEngineDesign.md` y
`docs/GreedyLayerStrategyDesign.md`.
