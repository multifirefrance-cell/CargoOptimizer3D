# Arquitectura de CargoOptimizer3D

Este documento describe la arquitectura definitiva congelada al cierre
de la fase 1 (infraestructura + arquitectura). Las decisiones aquí
resumidas están justificadas en detalle en `docs/ADR/`.

## Visión

CargoOptimizer3D debe poder distribuirse como aplicación de escritorio,
API REST, SDK embebido en un ERP, servicio o aplicación web, **sin
reescribir el motor**. Esto se consigue separando estrictamente el
motor de negocio (dominio + aplicación) de cualquier mecanismo de
entrega o cualquier detalle técnico externo.

## Capas y regla de dependencia

```
┌─────────────────────────────────────────────────────────┐
│ presentation   (desktop hoy; api / web en el futuro)     │
├─────────────────────────────────────────────────────────┤
│ infrastructure (JSON — 7.0; SQLite — 7.1; Excel — 8.0/8.1; PDF — 9.0/9.1) │
├─────────────────────────────────────────────────────────┤
│ application    (casos de uso, orquestación, puertos)     │
├─────────────────────────────────────────────────────────┤
│ optimization   (motor de optimización — fase 4.1, implementado)   │
├─────────────────────────────────────────────────────────┤
│ rules          (motor de reglas de negocio — fase 3)     │
├─────────────────────────────────────────────────────────┤
│ geometry       (cálculos espaciales — fase 2.2)          │
├─────────────────────────────────────────────────────────┤
│ domain         (LoadingSpace, LoadUnit, invariantes)      │
└─────────────────────────────────────────────────────────┘
```

Una capa solo puede importar las que están por debajo de ella en el
diagrama. `domain` no importa nada del propio proyecto. Esta regla se
verifica automáticamente con `import-linter` (ADR-0004); no es solo una
convención documental.

### `domain`

Entidades y reglas de negocio puras: `LoadingSpace`, `LoadUnit` y sus
invariantes geométricas y de negocio. Sin dependencias externas. Es el
paquete más estable del sistema: cambia solo cuando cambia el
modelo de negocio, nunca por un cambio de framework de UI o de base de
datos.

### `application`

Casos de uso (orquestación) y los puertos — interfaces Python
(probablemente `Protocol` o `ABC` mínimas, a decidir cuando haga
falta) que `infrastructure` implementará: repositorios de
persistencia, exportadores, proveedores de render. Depende de
`domain`, `geometry`, `rules` y `optimization`; nunca de
`infrastructure` ni `presentation`.

Primer caso de uso real (fase 10.1, ítem `OPT-01` de
`docs/ProductBacklog.md`): `MultiSpaceAssignmentEngine` — orquesta
varias ejecuciones de `PackingEngine.optimize(...)` (una por
`LoadingSpace`) para responder "¿cuántos espacios hacen falta para
este pedido, y qué va en cada uno?", sin reimplementar ninguna
búsqueda de colocación (eso sigue siendo de `optimization`). Ver
`docs/MultiSpaceAssignment.md` para el diseño completo.

```
application/
├── codes.py                      # MultiSpaceStopReason (StrEnum)
├── exceptions.py                  # ApplicationError, MultiSpaceAssignmentValidationError
├── models.py                      # MultiSpaceAssignmentRequest/Result, MultiSpaceProgress
└── multi_space_assignment.py      # MultiSpaceAssignmentEngine.assign(...)
```

### `infrastructure`

Adaptadores concretos de los puertos definidos en `application`.
Desde la fase 7.0 contiene `infrastructure/persistence/` (repositorio
de proyectos `.cargo3d`, JSON propio — ver `docs/ProjectFiles.md`).
Desde la fase 7.1 contiene además `infrastructure/database/` (catálogo
de productos, perfiles de espacio e historial en SQLite — ver
`docs/Database.md`; desde la fase 8.1 incluye también los perfiles de
mapeo de columnas de Excel, en la misma base de datos). Desde la fase
8.0 contiene además `infrastructure/excel/` (importación/exportación
profesional de `.xlsx` con `openpyxl` — ver `docs/Excel.md`; la fase
8.1 añade mapeo de columnas, vista previa, importación parcial,
duplicados, informes y exportación avanzada sobre ese mismo módulo,
sin nuevos formatos — ver `docs/ExcelAutomation.md`). El sistema de
informes PDF (`infrastructure/pdf/`, ReportLab) se diseñó en la fase
9.0 (`docs/PdfReportDesign.md`, ADR-0012) y se implementó en la fase
9.1 exactamente según ese diseño — ver `docs/PdfReports.md` para la
implementación real (cinco tipos de informe, integración con la
captura del visor 3D, plantillas como datos).

Depende de `domain` (y, desde la fase 10.1, también de `application`
para los casos de uso reales que orquesta, como la asignación
multi-espacio; los tres subpaquetes de infraestructura anteriores a esa
fase solo necesitan `domain` para reconstruir las entidades).

```
infrastructure/
├── persistence/
│   ├── exceptions.py               # ProjectFileError y subclases tipadas
│   ├── serialization.py            # domain <-> dict, función a función, sin __dict__/pickle
│   └── project_file_repository.py  # ProjectFileRepository: save/load/validate/backup, atómico
├── database/
│   ├── paths.py                    # get_user_database_path(): %LOCALAPPDATA%, sin depender de Qt
│   ├── exceptions.py                # DatabaseError y subclases tipadas
│   ├── orm_models.py                 # SQLAlchemy 2.x declarativo: catálogo, perfiles, historial
│   ├── migrations.py                 # initialize_database/migrate_database, schema_version
│   ├── engine.py                     # DatabaseManager: sesiones cortas, PRAGMA, backup, salud
│   ├── repositories.py               # 5 repositorios: catálogo, perfiles de espacio, perfiles de
│   │                                  #   mapeo de Excel (fase 8.1), 2 historiales
│   └── catalog_service.py            # CatalogService: fachada única hacia presentation
├── excel/
│   ├── exceptions.py                 # ExcelError y subclases tipadas
│   ├── row_parsing.py                 # Ayudas genéricas de parseo compartidas por los esquemas
│   ├── results.py                     # RowError, *ImportResult (nunca se importa una fila inválida en silencio)
│   ├── styles.py                      # Formato profesional compartido: cabeceras, bordes, tablas, autoajuste
│   ├── workbook_utils.py              # Apertura segura, cabeceras, iteración de filas, escritura atómica
│   ├── product_rows.py                # Esquema de columnas de LoadUnit (catálogo)
│   ├── loading_space_rows.py          # Esquema de columnas de LoadingSpace
│   ├── catalog_importer.py / catalog_exporter.py
│   ├── packing_list_importer.py       # Resuelve SKU vía un Callable inyectado, nunca importa SQLite directo
│   ├── loading_space_importer.py
│   ├── result_exporter.py             # PackingResult -> .xlsx con 5 hojas
│   ├── detection.py                   # detect_template_kind(): identifica la plantilla por cabeceras
│   ├── templates.py                   # Genera las 4 plantillas oficiales (examples/templates/)
│   ├── mapping.py                     # Fase 8.1: detección de alias, hoja remapeada en memoria
│   ├── import_preview.py              # Fase 8.1: clasificación nuevo/existente/duplicado/inválido
│   ├── import_plan.py                 # Fase 8.1: importación parcial + resolución de duplicados (función pura)
│   ├── import_report.py               # Fase 8.1: informe individual/masivo + exportación a .xlsx
│   └── advanced_export.py             # Fase 8.1: selección/orden/nombre de hojas, ocultar vacías
└── pdf/                               # Fase 9.1 (diseño en 9.0: docs/PdfReportDesign.md, ADR-0012)
    ├── exceptions.py                   # PdfError, PdfConfigError, PdfRenderError
    ├── styles.py                       # Tipografía, colores, TableStyle compartidos
    ├── layout.py                       # Cabecera/pie, numeración "Página X de Y", marca de agua
    ├── report_config.py                # CompanyProfile, ClientInfo, ReportSection, ReportConfig
    ├── report_content.py               # ReportContent + build_report_content() (único import de domain)
    ├── sections.py                     # Un build_*_section() por ReportSection
    ├── templates.py                    # ReportTemplate + los 5 informes oficiales, como datos
    └── report_builder.py               # generate_report(): único módulo que importa reportlab.platypus
```

### `presentation`

Mecanismos de entrega. Hoy contiene `presentation/desktop` (PySide6).
En el futuro, `presentation/api` (REST) o `presentation/web` se añaden
como hermanos, sin tocar el código de escritorio existente. Es la
única capa, junto con `infrastructure`, donde se permite importar
bibliotecas externas (Qt en este caso). Los recursos propios de un
adaptador de presentación (iconos, `.qrc`, plantillas HTML) viven
dentro de ese adaptador — p. ej. `presentation/desktop/resources/` —
nunca en un directorio compartido a nivel de proyecto, porque no son un
recurso del SDK sino de un mecanismo de entrega concreto.

Desde la fase 5.1, `presentation/desktop/` tiene esta forma:

```
presentation/desktop/
├── app.py               # arranque: QApplication, tema, MainWindow
├── main_window.py        # MainWindow: menús, toolbar, splitters, dock, status bar,
│                          #   construcción de PackingRequest, ciclo de vida del worker
│                          #   y ciclo de vida completo del proyecto (.cargo3d, fase 7.0)
├── icons.py               # carga de resources/icons/*.svg como QIcon
├── style.py                # paletas claro/oscuro + QSS (aspecto industrial)
├── settings.py              # AppSettings: wrapper de QSettings, claves centralizadas
├── workers/
│   └── optimization_worker.py  # OptimizationWorker(QThread): único punto que llama a PackingEngine
├── models/
│   ├── product_table_model.py            # QAbstractTableModel sobre list[LoadUnit]
│   ├── unpacked_table_model.py           # QAbstractTableModel sobre PackingResult.unpacked_units
│   ├── product_catalog_table_model.py    # QAbstractTableModel de solo lectura sobre el catálogo (7.1)
│   └── loading_space_profile_table_model.py  # ídem sobre perfiles de espacio (fase 7.1)
├── panels/
│   ├── loading_space_form_panel.py       # formulario completo; ahora vive en un diálogo bajo demanda
│   ├── loading_space_summary_panel.py    # rediseño "workspace operativo": Tipo/Perfil/resumen compacto
│   ├── product_quick_add_panel.py        # rediseño "workspace operativo": buscador SKU + cantidad + agregar
│   ├── product_table_panel.py            # "Lista de carga" simplificada (SKU/Nombre/Cantidad/Peso total)
│   ├── results_panel.py          # resumen numérico del último PackingResult
│   ├── unpacked_table_panel.py   # tabla de instancias no cargadas
│   ├── warnings_panel.py         # PackingResult.warnings
│   ├── log_panel.py              # registro de inicio/fin/duración/cancelación/errores
│   └── selection_details_panel.py  # detalle de la caja seleccionada en el visor 3D
├── dialogs/                          # diálogos modales (fase 7.1; fase 8.1 añade los 4 siguientes)
│   ├── product_catalog_dialog.py             # listar/buscar/CRUD/añadir al proyecto; acepta drag&drop (8.1)
│   ├── catalog_product_editor_dialog.py      # editor modal de un LoadUnit de catálogo
│   ├── loading_space_editor_dialog.py        # envuelve LoadingSpaceFormPanel bajo "Cambiar medidas…"
│   ├── loading_space_profiles_dialog.py      # listar/buscar/CRUD/aplicar perfiles
│   ├── loading_space_profile_editor_dialog.py  # reutiliza LoadingSpaceFormPanel tal cual
│   ├── column_mapping_dialog.py               # Fase 8.1: asistente de mapeo de columnas + perfiles
│   ├── duplicate_resolution_dialog.py         # Fase 8.1: Actualizar/Duplicar/Ignorar por SKU
│   ├── import_preview_dialog.py               # Fase 8.1: contadores + modo de importación parcial
│   └── bulk_import_dialog.py                  # Fase 8.1: varios archivos, resumen final
├── drag_drop.py                     # Fase 8.1: detección de `.xlsx` local en eventos de arrastre
├── viewer/                          # visor 3D — hermano de panels/models/workers, NO de infrastructure
│   ├── __init__.py
│   ├── widget.py                    # Packing3DViewer(QWidget): contrato público + fallback
│   ├── scene_controller.py          # Plotter de PyVista, actores, cámara, picking, selección
│   ├── scene_builder.py             # PackingResult + load_units_by_id -> SceneModel (sin VTK/Qt)
│   ├── color_registry.py            # SKU -> color hex determinista entre ejecuciones
│   ├── models.py                    # SceneModel, PlacementVisualModel (dataclasses)
│   └── constants.py                 # paleta, opacidades, grosores — config. visual centralizada
└── resources/icons/*.svg
```

`presentation/desktop/panels/viewport_3d_placeholder.py` (fase 5.0/6.0)
se eliminó en la fase 6.1: `Packing3DViewer` (con su propio fallback
interno cuando el 3D no está disponible) ocupa su lugar en
`work_area_splitter`. Detalle completo de la implementación real en
`docs/ThreeDViewer.md`.

`viewer/` depende de `domain` (igual que el resto de
`presentation/desktop`) y de `PyVista`/`PyVistaQt`/`vtk` (dependencias
de terceros añadidas en la fase 6.1 — ADR-0010). **No** depende de
`cargo_optimizer.optimization`: recibe siempre un `PackingResult` ya
calculado (`display_result(result, load_units_by_id)`), nunca ejecuta
el motor — ver ADR-0011. Esta restricción no la impone hoy
`import-linter` de forma automática (`presentation` puede importar
legítimamente `optimization`, como ya hace
`workers/optimization_worker.py`): es disciplina de diseño, documentada
aquí y en `CLAUDE.md`.

Todos los modelos y paneles pueden importar `cargo_optimizer.domain`
(está por debajo de `presentation` en la regla de dependencia) — de
hecho `ProductTableModel` y `LoadingSpaceFormPanel` construyen
`LoadUnit`/`LoadingSpace` reales, no una copia paralela del esquema de
dominio. Desde la fase 5.1, `workers/optimization_worker.py` es el
**único** módulo de `presentation/desktop` que importa
`cargo_optimizer.optimization` (`PackingEngine`, `CancellationToken`) —
`main_window.py` importa el resto de la API pública
(`PackingRequest`, `PackingProgress`, `GreedyExtremePointStrategy`,
`PackingRequestValidationError`) solo para construir la solicitud y
mostrar estado, nunca para reimplementar nada del motor.
`OptimizationWorker` es un `QThread`: `PackingEngine.optimize(...)`
nunca se ejecuta en el hilo de la interfaz (ver
`docs/OptimizationEngine.md` para el rendimiento real, que es
precisamente por qué bloquear la GUI durante una ejecución no era
aceptable).

Desde la fase 7.1, `main_window.py` recibe un `CatalogService | None`
opcional (`infrastructure/database/`, ver `docs/Database.md`) y lo usa
directamente (sin una capa `application` intermedia, mismo criterio ya
establecido para `ProjectFileRepository` en la fase 7.0) para abrir los
diálogos de catálogo/perfiles y registrar historial. `None` significa
modo limitado: la aplicación sigue abriendo y los proyectos `.cargo3d`
siguen funcionando, solo se deshabilitan las acciones de
catálogo/perfiles/historial.

Desde la fase 8.0, `main_window.py` importa directamente
`infrastructure/excel/` (`import_catalog`, `export_catalog`,
`import_packing_list`, `import_loading_spaces`, `export_packing_result`,
`detect_template_kind`) para las acciones de importación/exportación de
Excel — ver `docs/Excel.md`. El importador de Packing List no depende
de `infrastructure/database` directamente: recibe
`CatalogService.products.get_by_sku` como un `Callable` inyectado desde
`main_window.py`, manteniendo `infrastructure/excel` comprobable sin una
base de datos real.

Desde la fase 8.1, `_run_smart_catalog_import` en `main_window.py` es
el único punto que orquesta el flujo automatizado completo (mapeo →
vista previa → resolución de duplicados → escritura transaccional vía
`ProductCatalogRepository.apply_bulk`) para las tres acciones de
importación de catálogo y para arrastrar y soltar sobre
`ProductCatalogDialog`; `MainWindow.dragEnterEvent`/`dropEvent`
reutilizan `detect_template_kind` (mismo criterio que "Archivo >
Importar Excel") para soltar directamente sobre la ventana principal.
Ver `docs/ExcelAutomation.md` para el detalle completo.

## Motores de negocio: geometry, rules, optimization

```
src/cargo_optimizer/
├── domain/
├── geometry/       # fase 2.2 — implementado, depende solo de domain
├── rules/          # fase 3 — implementado, depende de domain y geometry
├── optimization/   # fase 4.1 — implementado, depende de domain, geometry y rules
├── application/    # orquesta domain + geometry + rules + optimization (fase 6+)
├── infrastructure/
└── presentation/
```

`geometry` (fase 2.2), `rules` (fase 3) y `optimization` (fase 4.1) ya
existen. `geometry`: cajas ortoédricas, límites, colisiones, soporte
físico, puntos candidatos y validación de layouts — ver
`docs/GeometryEngine.md` y ADR-0006. `rules`: motor de reglas de
negocio puro y determinista (orientaciones permitidas, extintores,
apilamiento, fragilidad, peso) que responde si una colocación es
válida sin decidir dónde colocar nada — ver `docs/RulesEngine.md` y
ADR-0007. `optimization`: motor de empaquetado real, con la estrategia
`greedy_extreme_point_v1` (`GreedyExtremePointStrategy`) — ver
`docs/OptimizationEngine.md` (implementación real),
`docs/OptimizationEngineDesign.md` y
`docs/GreedyLayerStrategyDesign.md` (diseño original de fase 4.0,
conservados como historial), ADR-0008 y ADR-0009. La fase 4.2 optimizó
el rendimiento interno de `optimization` (caché incremental de
bounding box, poda de candidatos) sin cambiar esta estructura ni la API
pública — ver `docs/OptimizerPerformance.md`.

Se crean como hermanos de `domain` (no como subpaquetes de `domain` ni
de `application`) porque son subsistemas sustanciales con algoritmos
propios (bin packing, resolución de restricciones), no simples
entidades ni casos de uso de orquestación. Mezclar esta decisión con la
lista de capas (`domain`/`geometry`/`rules`/`optimization`/`application`/`infrastructure`/`presentation`)
sería confundir dos ejes de descomposición distintos — ver ADR-0001,
sección de rechazo explícito de esa alternativa.

## El núcleo como SDK

`domain` + `optimization` + `application` forman el SDK público del
proyecto. Ya funciona, sin ninguna dependencia de UI instalada:

```python
from cargo_optimizer import PackingEngine, PackingRequest
```

Ver ADR-0003 para el detalle de esta garantía y cómo se protege.

## Verificación de la arquitectura

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\lint-imports.exe                    # import-linter — regla de capas
.\.venv\Scripts\python.exe -m pytest
```
