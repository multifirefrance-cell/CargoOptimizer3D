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
| 6.0 | Diseño del visor 3D | Ninguno (solo documentación: `docs/ThreeDViewerDesign.md`, `docs/ThreeDViewerImplementationPlan.md`, ADR-0010, ADR-0011) | **Completada** |
| 6.1 | Visor 3D — implementación mínima | `presentation/desktop/viewer` (nuevo, hermano de `panels`/`models`/`workers`) | Pendiente |
| 6.2 | Visor 3D — filtros, etiquetas, vistas, captura de imagen | `presentation/desktop/viewer` (mismos módulos) | Pendiente |
| 6.3 | Visor 3D — animación y escala | `presentation/desktop/viewer` (mismos módulos) | Pendiente |
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

## Nota sobre la numeración y el paquete de la fase 6

La fila original de la fase 6 decía "Visualización 3D — `infrastructure`
(adaptador VTK)". Al diseñar la fase formalmente
(`docs/ThreeDViewerDesign.md`, sección 3) se determinó que el visor
**no** pertenece a `infrastructure` (que son adaptadores de
persistencia/exportación detrás de puertos de `application`, y
`application` ni siquiera existe todavía) sino a
`presentation/desktop/viewer/`, hermano de `panels/`/`models/`/
`workers/` ya existentes — el visor es un mecanismo de presentación de
datos ya calculados, no un adaptador de infraestructura. Se corrige
aquí la tabla para reflejarlo. La fase 6 se subdivide además en **6.0
Diseño** (completada, esta sesión), **6.1 Implementación mínima**,
**6.2 Enriquecimiento** (filtros, etiquetas, vistas predefinidas,
captura de imagen) y **6.3 Escala y animación** — mismo motivo que las
fases 2, 4 y 5: separar diseño de implementación, y dentro de la
implementación, lo mínimo funcional de lo que puede esperar a que 6.1
esté en uso real. Detalle completo del reparto en
`docs/ThreeDViewerImplementationPlan.md`.

## Estado actual

Fin de fase 6.0: diseño formal del visor 3D, sin código funcional
nuevo. `docs/ThreeDViewerDesign.md` fija la tecnología (PyVista +
PyVistaQt, confirmada frente a VTK directo, `QOpenGLWidget` propio y
VisPy tras comparación formal — ADR-0010), la arquitectura
(`presentation/desktop/viewer/`, seis archivos en vez de los diez
sugeridos originalmente, con criterio explícito de cuándo separar los
tres que se fusionan en `scene_controller.py`), el contrato del widget
(`Packing3DViewer.display_result(result, load_units_by_id)` como única
puerta de entrada de datos — ADR-0011), el modelo de escena
(`SceneModel`/`PlacementVisualModel`), cómo `SceneBuilder` resuelve
SKU/nombre/color de cada `Placement` (entregando también un mapping
`UUID -> LoadUnit`, el mismo patrón ya usado para `UnpackedUnit` desde
la fase 5.1), coordenadas (sin permutar ejes: "Z arriba" es una vista
de cámara, no una transformación de datos), representación de
`LoadingSpace` y `Placement`, colores (por SKU, determinismo real entre
ejecuciones — no con `hash()` de Python, que está aleatorizado por
proceso), cámara, picking/selección con prevención de ciclos de señal,
qué filtros quedan dentro/fuera de 6.1, integración con `MainWindow`
sin romper el `QThread`/progreso/cancelación/temas/`QSettings`/tests
offscreen ya existentes, rendimiento (expectativas razonadas, no
medidas), temas, captura de imagen y animación futuras, fallback
cuando 3D no está disponible (la aplicación debe abrir igual), riesgos
de empaquetado, y estrategia de pruebas en los cuatro niveles ya
establecidos por el proyecto. `docs/ThreeDViewerImplementationPlan.md`
separa el trabajo futuro en 6.1 (mínimo funcional), 6.2 (filtros,
etiquetas, vistas predefinidas, captura de imagen) y 6.3 (animación,
capas, cortes, explosión, escala). No se ha instalado ninguna
dependencia, no se ha tocado `domain`/`geometry`/`rules`/`optimization`
(verificado con `git diff` vacío en los cuatro paquetes antes del
commit), y el placeholder actual
(`viewport_3d_placeholder.py`) sigue sin cambios. 386 pruebas en verde,
sin ninguna nueva en esta fase (fase exclusivamente documental, mismo
criterio que la fase 4.0). La siguiente sesión de desarrollo debe
abordar la **fase 6.1** (implementación mínima del visor), siguiendo el
plan ya escrito en `docs/ThreeDViewerImplementationPlan.md`. Si el
rendimiento del motor a gran escala (250+ instancias) sigue siendo
prioritario en paralelo, ver `docs/OptimizerPerformance.md` para la
alternativa pendiente (índice espacial dentro de `rules`/`geometry`,
con ADR explícito).
