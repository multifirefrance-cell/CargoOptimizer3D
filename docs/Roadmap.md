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
| 9.1 | Informes PDF — implementación | `infrastructure/pdf` (nuevo) | **Completada** |
| 10 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 10.1 | Product Backlog comercial (`docs/ProductBacklog.md`, sin código) | Ninguno (solo documentación) | **Completada** |
| 10.1+ | Ejecución del Product Backlog, ítem por ítem (`OPT-01` motor + integración de interfaz, `OPT-02` caché de rendimiento) | Variable según el ítem — ver `docs/ProductBacklog.md` | En curso |
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
subdivide como **fase 9**: **9.0** (diseño puro, `docs/PdfReportDesign.md`
y ADR-0012) y **9.1** (implementación real, un cuarto encargo
inmediatamente posterior) — mismo criterio de separar diseño de
implementación que ya se aplicó a las fases 4, 6 y ahora esta. La
antigua fila 9 ("Integración ERP") pasa a **10**, y "Versión comercial"
pasa de 10 a **11**. Ninguna fase completada cambia de número; solo se
renumeran las que todavía estaban pendientes, mismo principio que ya
guio las notas de las fases 2, 5, 6, 7 y 8.

## Nota sobre la transición al Product Backlog (fase 10.1 en adelante)

Hasta la fase 9.1, el roadmap era la única fuente de verdad de qué
construir después, numerada secuencialmente `X.Y`. La fase 10.1
("Construcción del Product Backlog comercial") reemplaza esa
numeración secuencial por un backlog priorizado por valor
(`docs/ProductBacklog.md`), organizado en EPICs (`OPT`, `LOG`, `VIS`,
`UX`, `DAT`, `REP`, `INT`, `ADM`, `COM`) con un ID estable por ítem
(p. ej. `OPT-01`) en vez de un número de fase. A partir de aquí, esta
tabla solo registra hitos de alto nivel (cuándo se completó el backlog,
qué ítem se está ejecutando); el detalle de alcance, criterios de
aceptación y estado de cada pieza de trabajo vive en
`docs/ProductBacklog.md`, columna "Estado" de cada ítem — esa es la
fuente de verdad a partir de ahora, no una fila nueva por cada ítem en
esta tabla.

El primer ítem ejecutado tras el backlog es `OPT-01` (asignación
automática multi-espacio): implementado como primer caso de uso real
de `application` — ver `docs/MultiSpaceAssignment.md`. Integrado
después en `presentation/desktop` (acción "Optimización multi-espacio…",
`F6`, mismo patrón de `QThread`/`CancellationToken` que la optimización
de un solo espacio) — ver `docs/MultiSpaceAssignment.md`, §9. `OPT-02`
(rendimiento) se abordó de forma acotada: caché de cajas ya conocidas
entre `optimization` y `rules`, sin cambiar la complejidad — ver
`docs/OptimizerPerformance.md`, sección "Fase OPT-02".

## Estado actual

Fin de fase 9.1: sistema de informes PDF completamente implementado —
ver `docs/PdfReports.md` (implementación real: los ocho módulos de
`infrastructure/pdf/`, los cinco tipos de informe con su contenido
exacto, configuración de empresa/cliente/idioma/colores/cabecera/pie/
numeración/marca de agua, integración con la captura del visor 3D,
sistema de plantillas, la acción "Archivo > Exportar PDF…" en
`MainWindow`, pruebas y smoke test). El diseño previo
(`docs/PdfReportDesign.md`, fase 9.0) y ADR-0012 se implementaron
exactamente como se diseñaron, sin reabrir ninguna decisión de
arquitectura: `ReportTemplate` como datos (cinco constantes, no cinco
clases), `reportlab` aislado de `domain` en
`report_content.py`/`report_config.py`, y la captura del visor 3D
recibida como `bytes | None` ya calculada (`Packing3DViewer.
export_screenshot_png()`, nueva capacidad mínima añadida a
`presentation/desktop/viewer/` en esta fase — no toda la fase 6.2,
solo la captura). `reportlab>=4.2,<5` se añade como dependencia de
producción; `pypdf` como dependencia de desarrollo, usada únicamente
para validar los PDF generados en las pruebas (nunca para generarlos).
`domain`/`geometry`/`rules`/`optimization`/`infrastructure/database`/
`infrastructure/excel` sin ningún cambio.

La siguiente sesión de desarrollo puede abordar la **fase 6.2**
(filtros, etiquetas, modos de color, vistas predefinidas del visor 3D
— la captura de imagen en sí ya se resolvió en la fase 9.1) o la
**fase 10** (integración ERP), según prioridad — a decidir
explícitamente antes de empezar. Si el rendimiento del motor a gran
escala (250+ instancias) sigue siendo prioritario en paralelo, ver
`docs/OptimizerPerformance.md` para la alternativa pendiente (índice
espacial dentro de `rules`/`geometry`, con ADR explícito).

Tras `OPT-01`/`OPT-02` y su integración en la interfaz, se ejecutó una
auditoría transversal de estabilización ("Beta 1.0", versión
`1.0.0b1`): no es una fase ni un ítem nuevo del Product Backlog, sino
un cierre de calidad sobre todo lo ya construido (bugs reales de
interfaz/threading/persistencia encontrados y corregidos, sin
funcionalidades nuevas ni cambios de arquitectura) — ver `CHANGELOG.md`
para el detalle completo de qué se corrigió.

Tras Beta 1.0, un encargo de UX ("workspace operativo", estilo
EasyCargo sin copiar su diseño) reorganizó `presentation/desktop` en
dos zonas: izquierda (espacio de carga compacto vía
`LoadingSpaceSummaryPanel` + "Cambiar medidas…" en
`LoadingSpaceEditorDialog`; alta rápida de producto vía
`ProductQuickAddPanel`, buscador SKU/nombre + cantidad; "Lista de
carga" simplificada en `ProductTablePanel`, solo SKU/Nombre/Cantidad/
Peso total) y derecha (visor 3D protagonista). El panel "Guía"
(`ProjectTreePanel`, de pasos 1-5) se elimina por completo: ya no hace
falta explicar el flujo con un panel aparte. Solo toca
`presentation/desktop`; `domain`/`geometry`/`rules`/`optimization`/
`application`/`infrastructure` sin ningún cambio.

Un encargo posterior de diseño ("celdas fijas, sin barras móviles")
eliminó los tres `QSplitter` restantes del workspace (todo pasa a
`QVBoxLayout`/`QHBoxLayout` de proporciones fijas), rediseñó el
buscador de "Agregar productos a la carga" como un `QComboBox`
editable (la lista completa del catálogo se ve con un clic, sin
escribir nada), corrigió que `MultiSpaceResultsPanel` inflaba el
mínimo de todo `results_tabs` (envuelto ahora en `QScrollArea`), y
corrigió un bug real de pérdida de datos: `CatalogProductEditorDialog`
leía `QComboBox.currentData()` directamente para
`package_type`/`extinguisher_agent`, y el redondeo por `QVariant` de
PySide6 puede devolver un `str` plano en vez del `StrEnum` original —
`ProductCatalogRepository.add()`/`update()` fallaban con
`AttributeError` silencioso, así que "Crear nuevo SKU…" parecía
funcionar pero nunca guardaba el producto. Solo toca
`presentation/desktop`; sin cambios en las demás capas.

El mismo encargo derivó en una investigación real de rendimiento (un
usuario reportó que 1300 unidades de una caja pequeña solo cargaban
148 antes de cancelar): perfilado real confirmó, con un caso concreto
y evidencia nueva, el mismo diagnóstico ya documentado en las fases
4.2/OPT-02 (`docs/OptimizerPerformance.md`) — el costo domina en
comprobaciones O(n) de colisión/soporte sin índice espacial, no en
`optimization` ni en la interfaz. Por decisión explícita del
arquitecto del proyecto, la investigación se cerró **sin escribir
código, sin tocar `domain`/`geometry`/`rules`/`optimization`, y sin
redactar todavía el ADR del índice espacial** — ver
`docs/OptimizerPerformance.md`, sección "OPT-03 → OPT-11
(2026-07-17)", y `docs/ProductBacklog.md`, ítem **OPT-11** (postergado,
sin ADR). La prioridad vuelve por completo al desarrollo funcional de
la Beta 1.0; no abrir nuevas investigaciones de rendimiento hasta que
esa Beta esté funcionalmente terminada.

**Actualización (auditoría técnica pre-Beta, cierra el hueco de
narrativa entre lo anterior y el estado real hoy):** en contra de la
decisión de cierre citada arriba, el índice espacial se implementó
poco después dentro del mismo periodo de trabajo (commit `8396576`,
ver ADR-0015 — documento retroactivo escrito durante esta misma
auditoría) y se corrigió/amplió en varias fases posteriores, todas
documentadas en `CLAUDE.md` (invariantes del motor de optimización) y
`docs/OptimizerPerformance.md`: **OPT-13** (eliminación del peso
soportado acumulado/propagado y del apilamiento recursivo — esto es lo
que hizo seguro, de forma independiente, generalizar el índice
espacial), **OPT-14** (valor por defecto de `max_stack_count` = 30),
**OPT-15** (eliminación de la excepción automática de apilamiento de
extintores, ADR-0014), **OPT-16** (corrección de varios puntos que no
aprovechaban el índice espacial ya existente — caso real de 2000
unidades: ~2973 s → ~552-960 s, mismo resultado exacto), **OPT-17**
(orientaciones por defecto reducidas, patrón de filas/capas, caché de
`support_ratio`, color pastel automático) y **OPT-18** (plantilla
Excel descargable, caché de saturación temprana por SKU, agrupación de
actores del visor 3D por forma+color). Entre estas fases y la Beta
1.0, se completó también el **empaquetado Windows** (PyInstaller
onedir + Inno Setup, ADR-0013, directorio `packaging/`): el instalador
`CargoOptimizer3D_Beta_Setup.exe` es un entregable real, no solo un
script de desarrollo. Para el detalle completo de cada fase de
rendimiento, `docs/OptimizerPerformance.md` y `CLAUDE.md` son siempre
la fuente actualizada — esta sección se mantiene como narrativa
histórica y se seguirá extendiendo hacia adelante, no reescribiendo lo
ya escrito.
