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
| 5.0 | Base de la interfaz de escritorio | `presentation/desktop` (ventana principal, paneles, sin conectar el motor) | **Completada** |
| 5.1 | Conectar el motor con la interfaz | `presentation/desktop` (invocar `PackingEngine` desde `MainWindow`) | **Completada** |
| 6 | Visualización 3D | `infrastructure` (adaptador VTK) | Pendiente |
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

## Nota sobre la numeración de las fases 5 y 6

La numeración original de este roadmap tenía "5 = Visualización 3D" y
"6 = Interfaz". Al encargar la fase de interfaz se pidió explícitamente
como **Fase 5.0**, con la vista 3D remitida a la **Fase 6** (el propio
placeholder de `Viewport3DPlaceholder` dice "Vista 3D disponible en la
Fase 6"): la interfaz de escritorio pasa a ir antes que VTK, no
después, porque tiene sentido tener ya una aplicación navegable antes
de invertir en el render 3D. Se actualiza aquí la tabla para que
coincida con lo realmente construido, siguiendo el mismo criterio que
la nota anterior (no renumerar en cascada fases ya cerradas sin
necesidad; aquí sí hacía falta porque 5 y 6 todavía no se habían
implementado). Fase 5 pasa a subdividirse en **5.0 Base de la interfaz**
(completada) y **5.1 Conectar el motor con la interfaz** (pendiente),
por el mismo motivo que las fases 2 y 4: no se puede diseñar
`PackingEngine` en la UI en la misma entrega que se diseña la ventana
que lo va a alojar.

## Estado actual

Fin de fase 5.1: la interfaz de escritorio ya ejecuta el motor real de
principio a fin. `MainWindow._build_packing_request()` lee el
`LoadingSpace` del formulario y los `LoadUnit` de la tabla de
productos, construye una `PackingRequest` real (o explica con claridad,
vía `QMessageBox`, por qué no puede si falta algo) y "Ejecutar
optimización" la despacha a `OptimizationWorker`
(`presentation/desktop/workers/`), un `QThread` dedicado que llama a
`PackingEngine.optimize(...)` con su propio `CancellationToken` y
reenvía `PackingProgress`/`PackingResult` a la interfaz por señales —
la optimización nunca bloquea el hilo de la GUI. "Cancelar" activa el
`CancellationToken`; la interfaz queda consistente (controles
rehabilitados, barra de progreso oculta) en cuanto el hilo termina,
sin bloquear esperando. Los resultados se reparten en cuatro pestañas
del panel inferior: Resumen (`ResultsPanel`, ahora con cantidad
pendiente y conteo de avisos), No cargados (`UnpackedTablePanel`:
SKU/Instancia/Razón/Código sobre las `UnpackedUnit` reales), Avisos
(`WarningsPanel`, sobre `PackingResult.warnings`) y Registro
(`LogPanel`: inicio, fin, duración, cancelación y errores, con marca de
tiempo). Todo error real (`PackingRequestValidationError`,
`OptimizationInternalError` o cualquier excepción inesperada del hilo
del motor) se muestra con `QMessageBox`, nunca solo por consola. El
motor (`domain`/`geometry`/`rules`/`optimization`) sigue intacto: esta
fase solo consume su API pública
(`PackingEngine`/`PackingRequest`/`PackingProgress`/`CancellationToken`),
verificado por `git diff` vacío en esos cuatro paquetes antes del
commit. 386 pruebas en verde (370 previas + 16 nuevas: `OptimizationWorker`
en hilo real y síncrono, `UnpackedUnitTableModel`, y la integración
completa de `MainWindow` — construcción de solicitud, validaciones,
ejecución, cancelación, error, resultados —, todas bajo la plataforma
Qt `offscreen`). No se ha escrito código de visualización 3D,
persistencia, exportación/importación real, ni Undo/Redo. La siguiente
sesión de desarrollo debe abordar la **fase 6** (visualización 3D),
reutilizando este mismo flujo de ejecución en segundo plano para
alimentar el visor con los `Placement` del `PackingResult`. Si el
rendimiento del motor a gran escala (250+ instancias) sigue siendo
prioritario en paralelo, ver `docs/OptimizerPerformance.md` para la
alternativa pendiente (índice espacial dentro de `rules`/`geometry`,
con ADR explícito).
