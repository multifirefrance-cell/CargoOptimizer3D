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
| 6.1 | Visor 3D — implementación mínima | `presentation/desktop/viewer` (nuevo, hermano de `panels`/`models`/`workers`) | **Completada** |
| 6.2 | Visor 3D — filtros, etiquetas, vistas, captura de imagen | `presentation/desktop/viewer` (mismos módulos) | Pendiente |
| 6.3 | Visor 3D — animación y escala | `presentation/desktop/viewer` (mismos módulos) | Pendiente |
| 7.0 | Persistencia de proyectos (`.cargo3d`, JSON versionado) | `infrastructure/persistence` (nuevo) | **Completada** |
| 7.1 | Catálogo de productos y perfiles reutilizables (SQLite/SQLAlchemy) | `infrastructure/database` (nuevo) | **Completada** |
| 8.0 | Importación y exportación profesional de Excel (`.xlsx`) | `infrastructure/excel` (nuevo) | **Completada** |
| 8.1 | Automatización profesional del flujo Excel (mapeo de columnas, perfiles, vista previa, importación parcial, duplicados, drag&drop, importación masiva, informe, exportación avanzada) | `infrastructure/excel` (mismo paquete), `infrastructure/database` (perfiles de mapeo), `presentation/desktop` (4 diálogos nuevos + drag&drop) | **Completada** |
| 9.0 | Diseño del sistema profesional de informes PDF | Ninguno (solo documentación: `docs/PdfReportDesign.md`, ADR-0012) | **Completada** |
| 9.1 | Informes PDF — implementación | `infrastructure/pdf` (nuevo) | Pendiente |
| 10 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 11 | Versión comercial | — | Pendiente |

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

## Nota sobre la numeración de la fase 7

La fila original de la fase 7 era simplemente "Persistencia —
`infrastructure` (adaptador SQLAlchemy/SQLite)". El encargo real
distinguió, dentro de "persistencia", dos necesidades distintas:
guardar y reabrir un **proyecto completo** (espacio, productos,
resultado, estado de la interfaz) en un archivo propio versionado, y
—en una fase futura, todavía no numerada en detalle— un catálogo
reutilizable de Load Units/perfiles respaldado por SQLite. Se subdivide
la fase 7 en **7.0** (persistencia de proyectos, JSON) y **7.1**
(catálogo de productos y perfiles reutilizables, SQLite/SQLAlchemy),
mismo criterio que las fases 2, 4, 5 y 6: no mezclar en una sola
entrega dos mecanismos de persistencia con formatos, ciclo de vida y
prioridad de uso distintos.

## Nota sobre la numeración de la fase 8

La fila original de la fase 8 era simplemente "Reportes —
`infrastructure` (adaptadores openpyxl/ReportLab)", mezclando dos
formatos de salida completamente distintos (una hoja de cálculo
editable y manipulable vs. un documento de solo lectura para imprimir o
archivar) bajo un mismo número de fase. Se subdivide en **8.0**
(importación y exportación profesional de Excel, `openpyxl`) y lo que
originalmente era 8.1 (reportes PDF, `ReportLab`) pasa a **8.2** —
mismo criterio que las fases 2, 4, 5, 6 y 7: no mezclar dos adaptadores
de infraestructura con bibliotecas, formatos y casos de uso distintos
en una sola entrega.

Un segundo encargo real, ya con la fase 8.0 completada y en uso, pidió
explícitamente hacer del módulo Excel "una herramienta realmente cómoda
para el trabajo diario de logística" — mapeo de columnas, perfiles
reutilizables, vista previa, importación parcial, resolución de
duplicados, drag&drop, importación masiva, informe y exportación
avanzada — sin ningún formato nuevo. Ese encargo ocupa el hueco **8.1**
que había quedado libre al mover PDF a 8.2, en vez de crear una fase
8.3 nueva: es una entrega intermedia entre "Excel básico funciona" (8.0)
y "reportes PDF", no una fase posterior a ambas.

## Nota sobre la numeración de la fase 9

Un tercer encargo, ya con la fase 8.1 completada, pidió explícitamente
"FASE 9.0 — Diseño del sistema profesional de informes PDF". Lo que
hasta entonces era la fila **8.2** ("Reportes PDF") se renombra y
subdivide como **fase 9**: **9.0** (diseño puro, esta entrega,
`docs/PdfReportDesign.md` y ADR-0012) y **9.1** (implementación,
pendiente) — mismo criterio de separar diseño de implementación que ya
se aplicó a las fases 4, 6 y ahora esta. La antigua fila 9
("Integración ERP") pasa a **10**, y "Versión comercial" pasa de 10 a
**11**. Ninguna fase completada cambia de número; solo se renumeran las
que todavía estaban pendientes, mismo principio que ya guio las notas
de las fases 2, 5, 6, 7 y 8.

## Estado actual

Fin de fase 9.0: diseño completo del sistema de informes PDF — ver
`docs/PdfReportDesign.md` (arquitectura de `infrastructure/pdf/`, los
cinco tipos de informe y su contenido exacto, configuración de
empresa/cliente/idioma/colores/cabecera/pie/numeración/marca de agua,
integración diseñada — no implementada — con el visor 3D, sistema de
plantillas, personalización futura, revisión crítica) y ADR-0012
(`ReportTemplate` como datos en vez de una jerarquía de clases por
informe, aislamiento de `reportlab` respecto a `domain`, captura del
visor 3D inyectada como `bytes | None`). **No se ha creado ningún
código funcional de PDF ni se ha añadido `reportlab` como
dependencia** — esta fase es exclusivamente de documentación, tal como
exigía el encargo. `domain`/`geometry`/`rules`/`optimization`/
`presentation`/`infrastructure/database`/`infrastructure/excel` sin
ningún cambio.

La siguiente sesión de desarrollo puede abordar la **fase 6.2**
(filtros, etiquetas, modos de color, vistas predefinidas, captura de
imagen del visor 3D — de hecho un prerrequisito útil, aunque no
bloqueante, para que los informes PDF de la fase 9.1 puedan incluir la
captura del visor) o la **fase 9.1** (implementación real de
`infrastructure/pdf`, con `reportlab` como dependencia nueva), según
prioridad — a decidir explícitamente antes de empezar. Si el
rendimiento del motor a gran escala (250+ instancias) sigue siendo
prioritario en paralelo, ver `docs/OptimizerPerformance.md` para la
alternativa pendiente (índice espacial dentro de `rules`/`geometry`,
con ADR explícito).
