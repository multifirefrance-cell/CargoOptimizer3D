# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Este proyecto aún no ha alcanzado la versión 1.0; el versionado 0.x
puede incluir cambios estructurales entre versiones menores.

## [0.15.1] - 2026-07-16

`OPT-02` (rendimiento del `PackingEngine`), parcial: caché de cajas ya
conocidas entre `optimization` y `rules`. Optimización de rendimiento
pura verificada con datos de perfilado actuales — cero cambio de
resultado, cero cambio de complejidad. Ver `docs/OptimizerPerformance.md`,
sección "Fase OPT-02", para el análisis completo (antes/después,
costo, limitaciones restantes).

### Changed

- `rules/context.py`: `PlacementRuleContext` gana
  `precomputed_existing_boxes: tuple[AxisAlignedBox, ...] | None = None`
  (por defecto `None`, mismo comportamiento de recálculo que antes —
  compatibilidad total con las pruebas unitarias existentes de
  `rules`) y una nueva propiedad `box_by_sequence_number` para
  búsqueda O(1) de la caja de un placement ya conocido.
- `rules/stacking_rules.py`: `find_direct_supporting_placements`,
  `count_stack_level`, `_all_transitive_supporters` y
  `_weight_resting_on` ganan un parámetro opcional
  `box_by_sequence_number` (por defecto `None`) para evitar
  reconstruir con `box_from_placement` una caja que el llamador ya
  conoce.
- `optimization/candidates.py`: `build_candidate` pasa
  `precomputed_existing_boxes=existing_boxes` (valor que ya recibía
  como parámetro, calculado incrementalmente por `PackingState` desde
  la fase 4.2) al construir el `PlacementRuleContext` — antes lo
  calculaba y lo tiraba sin usarlo para este propósito.

### Added

- `tests/rules/test_performance_cache_equivalence.py`: prueba
  explícita de que `evaluate_candidate_placement`,
  `evaluate_stack_count` y `evaluate_supported_weight` producen el
  mismo `RuleEvaluation` con y sin `precomputed_existing_boxes`, sobre
  un layout de tres niveles con límites de peso soportado.

### Performance

- Escenario mixto de referencia (60 instancias), mismo proceso,
  instrumentado con `cProfile`: 45.690 s → 38.660 s (−15.4 %).
  Llamadas a `box_from_placement`: 4 596 319 → 769 109 (−83.3 %).
  Suite completa (846 pruebas) sin ningún cambio de resultado.
- **No se alcanza una mejora de orden de magnitud**: la causa raíz
  restante (recorrido O(n) de `existing_placements` en
  colisión/soporte/apilamiento) es estructural, no de caché — reducir
  la complejidad exigiría un índice espacial real dentro de
  `rules`/`geometry`, deliberadamente fuera de esta fase por su riesgo
  de correctness. Ver la conclusión honesta en
  `docs/OptimizerPerformance.md`.

## [0.15.0] - 2026-07-16

Implementación de `OPT-01` (asignación automática multi-espacio),
primer ítem ejecutado del Product Backlog comercial
(`docs/ProductBacklog.md`, fase 10.1) y primer caso de uso real de la
capa `application`.

### Added

- `application/codes.py`: `MultiSpaceStopReason` (`all_packed` /
  `impossible_remaining` / `max_spaces_reached` / `cancelled`).
- `application/exceptions.py`: `ApplicationError`,
  `MultiSpaceAssignmentValidationError`.
- `application/models.py`: `MultiSpaceAssignmentRequest` (candidatos de
  `LoadingSpace` en orden de preferencia, `load_units`, límites
  opcionales por espacio y `max_spaces`), `MultiSpaceAssignmentResult`
  (un `PackingResult` por espacio usado, más los agregados
  consolidados) y `MultiSpaceProgress`.
- `application/multi_space_assignment.py`: `MultiSpaceAssignmentEngine`
  — orquesta varias ejecuciones de `PackingEngine.optimize(...)` (una
  por espacio). En cada ronda evalúa **todos** los
  `loading_space_candidates` (nunca se detiene en el primero que
  coloca algo) y elige el mejor resultado con una clave de comparación
  determinista y fija: mayor `packed_count`, luego mayor
  `used_volume_cm3`, luego mayor `used_weight_kg`, luego menor
  `loading_space.capacity_volume_cm3`, y el orden original de
  `loading_space_candidates` como desempate final. Sin búsqueda
  combinatoria entre rondas. Nunca reimplementa colocación, geometría
  ni reglas — eso sigue siendo de `optimization`/`rules`/`geometry`,
  sin cambios.
- `MultiSpaceAssignmentResult`: resumen global además de
  `space_results`, sin duplicar nada ya presente en cada
  `PackingResult` — todo calculado como propiedad: conteo de espacios
  usados por nombre de candidato (`spaces_used_by_candidate_name`),
  `overall_weight_utilization_percent` (`None` si ningún espacio usado
  declara `max_weight_kg`), `average_volume_utilization_percent`,
  `max_volume_utilization_percent`, `min_volume_utilization_percent`,
  `pending_count`.
- `docs/ProductBacklog.md`: Product Backlog comercial completo (fase
  10.1), incorporado al repositorio como referencia del proyecto.
- `docs/MultiSpaceAssignment.md`: diseño y uso de
  `MultiSpaceAssignmentEngine`, incluyendo el criterio exacto de
  selección del mejor candidato y el análisis de costo de evaluarlos
  todos.
- `tests/application/`: 28 pruebas nuevas (validación de la solicitud,
  un espacio basta, hacen falta varios, imposibilidad total, tope
  `max_spaces`, cancelación entre espacios, fallback cuando un
  candidato no coloca nada, selección del mejor candidato aunque el
  primero de la lista ya coloque algo, los dos niveles de desempate
  restantes, determinismo, progreso por espacio, resiliencia ante
  excepciones del callback, pedido vacío, y las propiedades agregadas
  incluidas las nuevas).

### Changed

- `application/__init__.py`: deja de estar vacío; expone la API
  pública del caso de uso y corrige su docstring (dependía solo de
  `domain` en el texto; ya dependía también de `geometry`/`rules`/
  `optimization` según el contrato de capas, ahora lo refleja).
- `docs/Roadmap.md`, `docs/Architecture.md`, `README.md`, `CLAUDE.md`:
  documentan la transición de fase 10.1 en adelante (el Product
  Backlog, no la numeración secuencial `X.Y`, es la fuente de verdad
  de qué construir después) y el nuevo contenido de `application/`.

### Not in scope

- Integración con `presentation/desktop` (menú, diálogo de candidatos,
  worker en segundo plano): el motor se entrega probado de forma
  independiente; conectarlo a la interfaz queda para un encargo
  posterior, mismo criterio que ya separó `optimization` (fase 4.1) de
  su conexión a la interfaz (fase 5.1).
- Minimización exacta del número de espacios usados (NP-duro),
  secuenciación multi-parada (`LOG-03`) y sugerencia automática de
  espacio (`LOG-05`): ítems propios del backlog, no de `OPT-01`.

## [0.14.0] - 2026-07-16

Implementación del sistema profesional de informes PDF (fase 9.1),
exactamente según el diseño de la fase 9.0 (`docs/PdfReportDesign.md`,
ADR-0012), sin reabrir ninguna decisión de arquitectura.

### Added

- `infrastructure/pdf/`: `exceptions.py` (`PdfError`/`PdfConfigError`/
  `PdfRenderError`), `styles.py` (tipografía, colores, `TableStyle`
  compartidos), `layout.py` (cabecera, pie, numeración "Página X de Y"
  vía un `Canvas` de dos pasadas, marca de agua), `report_config.py`
  (`CompanyProfile`, `ClientInfo`, `ReportSection`, `ReportConfig`,
  datos puros sin ningún import de `reportlab`), `report_content.py`
  (`ReportContent` + `build_report_content()`, único punto que importa
  `domain`), `sections.py` (una función por `ReportSection`:
  portada, resumen ejecutivo, imagen del visor, datos del espacio,
  productos cargados, productos no cargados, avisos, apéndice técnico,
  pie legal), `templates.py` (`ReportTemplate` + los cinco informes
  oficiales como datos — `EXECUTIVE_SUMMARY`, `TECHNICAL_FULL`,
  `PACKING_LIST`, `INTERNAL_DIAGNOSTIC`, `CLIENT_REPORT`) y
  `report_builder.py` (`generate_report()`, escritura siempre atómica).
- Los cinco tipos de informe PDF con su contenido completo (ver
  `docs/PdfReports.md` para la matriz de secciones por informe);
  el informe de cliente oculta columnas de posición, algoritmo/tiempo
  de ejecución y detalle técnico de motivos de no-carga; el informe
  interno de diagnóstico fuerza una marca de agua "USO INTERNO — NO
  DISTRIBUIR".
- `presentation/desktop/viewer`: `SceneController.export_screenshot_png()`
  y `Packing3DViewer.export_screenshot_png()` — captura PNG en memoria
  de la vista 3D actual, `None` si el visor no está disponible o si la
  captura falla por cualquier motivo, nunca una excepción.
- `MainWindow`: acción "Archivo > Exportar PDF…" (`_on_export_pdf`) —
  elige tipo de informe, carpeta y nombre; construye `ReportContent`
  con la captura del visor si está disponible; deshabilitada mientras
  una optimización está en curso (mismo criterio que "Exportar Excel…
  resultado").
- `pyproject.toml`: nueva dependencia de producción `reportlab>=4.2,<5`;
  nuevas dependencias de desarrollo `types-reportlab>=4.2` (Mypy
  estricto) y `pypdf>=5.0` (validación de los PDF generados en las
  pruebas — nunca usada para generarlos).
- 51 pruebas nuevas: los cinco tipos de informe, con/sin imagen del
  visor (incluida una imagen corrupta), con/sin logo, proyecto
  vacío/completo, `config_overrides` de cada plantilla, numeración
  multi-página, marca de agua, escritura atómica, error de
  configuración (`tests/infrastructure/pdf/`), y la acción "Exportar
  PDF…" completa en `MainWindow`
  (`tests/presentation/desktop/test_main_window_pdf_export.py`).
- `docs/PdfReports.md`: implementación real (los ocho módulos,
  contenido exacto de los cinco informes, configuración, integración
  con el visor 3D, integración en `MainWindow`, seguridad, pruebas,
  smoke test y sus limitaciones de verificación en este entorno).
- Smoke test real de extremo a extremo: un `CargoProject` real
  optimizado con el motor real (`PackingEngine.optimize`, sin simular
  nada), generación de los cinco informes oficiales, validados con
  `pypdf` (parser independiente de `reportlab`).

## [0.13.1] - 2026-07-15

Diseño del sistema profesional de informes PDF (fase 9.0). Fase
exclusivamente de documentación: no se implementa ningún generador
PDF, no se añade `reportlab` como dependencia y no se crea el paquete
`infrastructure/pdf/` todavía.

### Added

- `docs/PdfReportDesign.md`: arquitectura de `infrastructure/pdf/`
  (ocho módulos propuestos: `exceptions.py`, `styles.py`, `layout.py`,
  `report_config.py`, `report_content.py`, `sections.py`,
  `templates.py`, `report_builder.py`, con justificación de cada uno);
  los cinco tipos de informe (resumen ejecutivo, informe técnico
  completo, packing list optimizado, informe interno de diagnóstico,
  informe para cliente) con una matriz de contenido sección por
  sección; configuración de empresa/cliente/idioma/colores/cabecera/
  pie/numeración/marca de agua; integración diseñada (no implementada)
  con el visor 3D vía `ReportContent.viewer_screenshot_png: bytes |
  None`; sistema de plantillas (`ReportTemplate` como datos); diseño de
  personalización futura (activar/desactivar/reordenar secciones,
  plantillas propias del usuario); decisiones descartadas; revisión
  crítica del propio diseño.
- `docs/ADR/ADR-0012-arquitectura-del-sistema-de-informes-pdf.md`:
  `ReportTemplate` como datos en vez de una jerarquía de clases por
  informe; aislamiento de `reportlab` respecto a `domain`
  (`report_content.py`/`report_config.py` sin ningún import de la
  biblioteca de renderizado); captura del visor 3D inyectada como
  `bytes | None`, nunca generada dentro de `infrastructure/pdf`.
- Renumeración de fases pendientes en `docs/Roadmap.md`/`CLAUDE.md`:
  "Reportes PDF" pasa a fase **9** (9.0 diseño, esta entrega; 9.1
  implementación, pendiente); "Integración ERP" pasa de 9 a **10**;
  "Versión comercial" pasa de 10 a **11**. Ninguna fase completada
  cambia de número.

## [0.13.0] - 2026-07-15

Automatización profesional del flujo Excel (fase 8.1): sobre el módulo
Excel de la fase 8.0, sin ningún formato nuevo, se añade mapeo de
columnas con detección automática y perfiles reutilizables, vista
previa antes de importar, importación parcial, resolución de
duplicados, arrastrar y soltar, importación masiva, informe de
importación y exportación avanzada. Ver `docs/ExcelAutomation.md` para
el detalle completo.

### Added

- `infrastructure/excel/mapping.py`: alias de columna conocidos para
  catálogo/packing list/loading space, `detect_column_mapping`,
  `build_remapped_worksheet` (hoja reordenada y renombrada en memoria,
  reutiliza sin duplicar el bucle de conversión fila a fila de la fase
  8.0), `import_catalog_with_mapping`/`import_packing_list_with_mapping`/
  `import_loading_spaces_with_mapping`.
- `infrastructure/excel/import_preview.py`: `CatalogImportPreview` +
  `build_catalog_preview` (clasifica un `CatalogImportResult` en
  nuevos/existentes/duplicados/inválidos, sin escribir nada).
- `infrastructure/excel/import_plan.py`: `ImportPlan` +
  `build_import_plan`, función pura que aplica el modo de importación
  parcial (todas/seleccionadas/solo nuevas/solo actualizadas/solo
  válidas) y la resolución de duplicados
  (Actualizar/Duplicar/Ignorar, con "aplicar a todos" vía un valor por
  defecto).
- `infrastructure/excel/import_report.py`: `ImportReport`,
  `BulkImportReport` (con totales agregados), `build_import_report`,
  `export_import_report` (hojas Resumen y Errores).
- `infrastructure/excel/advanced_export.py`: `SheetSelection`,
  `export_packing_result_advanced` (elegir hojas, orden, nombre,
  ocultar vacías) sobre el mismo libro de cinco hojas de
  `result_exporter.py`.
- `infrastructure/database`: tabla y repositorio
  `ImportMappingProfileRepository` (perfiles de mapeo de columnas,
  cuatro perfiles oficiales integrados — Kupfer, Joan, Exanco, Formato
  estándar CargoOptimizer — creados por `ensure_builtin_profiles`),
  `ProductCatalogRepository.apply_bulk` (escritura transaccional
  todo-o-nada: una única `session_scope()` para todo el lote de
  altas/actualizaciones).
- `presentation/desktop/drag_drop.py`: `has_excel_url`/
  `first_excel_path`/`all_excel_paths`, usados por `MainWindow` y
  `ProductCatalogDialog` para aceptar arrastrar y soltar un `.xlsx`.
- Cuatro diálogos nuevos en `presentation/desktop/dialogs/`:
  `ColumnMappingDialog` (mapeo + guardar/aplicar perfiles),
  `DuplicateResolutionDialog` (Actualizar/Duplicar/Ignorar por SKU,
  "aplicar a todos"), `ImportPreviewDialog` (contadores + modo de
  importación parcial), `BulkImportDialog` (varios archivos, resumen
  final, guardar informe).
- `MainWindow`: acciones "Importar con mapeo de columnas…" e
  "Importación masiva de Excel…" en el menú Productos;
  `_run_smart_catalog_import` orquesta mapeo → vista previa →
  duplicados → escritura transaccional para las tres acciones de
  importación de catálogo; `dragEnterEvent`/`dropEvent` sobre la
  ventana principal despachan por tipo de archivo (mismo criterio que
  "Importar Excel…") con mapeo automático como último recurso antes de
  rendirse; `ProductCatalogDialog` acepta arrastrar y soltar
  directamente al catálogo SQLite.
- 93 pruebas nuevas: mapeo de columnas y round-trip
  (`tests/infrastructure/excel/test_mapping.py`), vista previa e
  importación parcial/duplicados (`test_import_preview_plan.py`),
  informes (`test_import_report.py`), exportación avanzada
  (`test_advanced_export.py`), perfiles de mapeo
  (`tests/infrastructure/database/test_import_mapping_profile_repository.py`),
  transaccionalidad de `apply_bulk` (ampliación de
  `test_product_catalog_repository.py`), los cuatro diálogos nuevos,
  drag&drop (`test_drag_drop.py`) y el flujo completo en `MainWindow`
  (`test_main_window_excel_automation.py`).
- `docs/ExcelAutomation.md` (mapeador de columnas, perfiles, vista
  previa, importación parcial, duplicados, drag&drop, importación
  masiva, informe, exportación avanzada, transaccionalidad, pruebas).

## [0.12.0] - 2026-07-15

Importación y exportación profesional de Excel (`.xlsx`, fase 8.0): un
usuario puede importar catálogos, packing lists y perfiles de Loading
Space desde Excel, y exportar el catálogo y el resultado de una
optimización con formato profesional. Ver `docs/Excel.md` para el
detalle completo.

### Added

- `infrastructure/excel/`: `exceptions.py`
  (`ExcelError`/`ExcelFileError`/`ExcelTemplateError`), `row_parsing.py`
  (ayudas genéricas de parseo: blanco, booleano, número, etiqueta de
  enum, compartidas entre esquemas), `results.py` (`RowError`,
  `CatalogImportResult`, `LoadingSpaceImportResult`,
  `PackingListImportResult` — ninguna fila inválida se importa nunca en
  silencio), `styles.py` (formato profesional compartido: cabeceras en
  negrita con relleno suave, bordes, tablas nativas de Excel,
  autoajuste aproximado de columnas), `workbook_utils.py` (apertura
  segura con traducción de errores, validación de cabeceras, iteración
  de filas, escritura atómica vía archivo temporal + `os.replace`).
- Esquemas de columnas: `product_rows.py` (`LoadUnit`: SKU, nombre,
  dimensiones, peso, cantidad, color, fragilidad, tipo de empaque,
  extintor, agente, peso nominal, apilamiento, orientaciones, notas) y
  `loading_space_rows.py` (`LoadingSpace`: nombre, categoría,
  dimensiones, peso máximo, posición de puerta, notas) — ambos aceptan
  tanto la etiqueta en español como el valor interno estable del enum.
- `catalog_importer.py`/`catalog_exporter.py` (`import_catalog`/
  `export_catalog`), `packing_list_importer.py` (`import_packing_list`,
  resuelve SKU vía un `Callable` inyectado — nunca depende de
  `infrastructure/database` directamente; suma cantidades para un SKU
  repetido en vez de tratarlo como error), `loading_space_importer.py`
  (`import_loading_spaces`), `result_exporter.py`
  (`export_packing_result`: cinco hojas — Resumen, Productos cargados,
  Productos no cargados, Warnings, Datos del espacio).
- `detection.py` (`detect_template_kind`): identifica si un `.xlsx` es
  un catálogo, un packing list o un espacio de carga por sus cabeceras,
  usado por la acción genérica "Importar Excel".
- `templates.py`: genera las cuatro plantillas oficiales
  (`CatalogTemplate.xlsx`, `PackingListTemplate.xlsx`,
  `LoadingSpaceTemplate.xlsx`, `OptimizationResultTemplate.xlsx`) con
  el propio código del paquete, guardadas en `examples/templates/`.
- `MainWindow`: acciones reales de importación/exportación de Excel en
  los menús Archivo ("Importar Excel…"/"Exportar Excel…", con
  detección automática del tipo de plantilla), Productos ("Importar
  catálogo (Excel)…"/"Exportar catálogo (Excel)…", destino: catálogo
  SQLite), Espacio de carga ("Importar desde Excel…") y Proyecto
  ("Importar Packing List…"/"Exportar resultado…"). El flujo de
  Packing List con SKU ausentes del catálogo ofrece
  Continuar/Cancelar. Las acciones que dependen del catálogo SQLite se
  deshabilitan en modo limitado.
- `pyproject.toml`: nuevas dependencias `openpyxl>=3.1,<4` (runtime) y
  `types-openpyxl>=3.1` (desarrollo, para Mypy estricto).
- 51 pruebas nuevas en `tests/infrastructure/excel/` (archivos
  corruptos, cabeceras faltantes o en otro orden, tipos incorrectos,
  SKU inexistentes, SKU duplicados, filas vacías, round-trip completo
  incluidas las cuatro plantillas oficiales) y 16 pruebas nuevas en
  `tests/presentation/desktop/test_main_window_excel_integration.py`
  (integración completa bajo `offscreen`, sin abrir nunca un diálogo
  real).
- `docs/Excel.md` (esquema de columnas, plantillas oficiales, formato
  profesional, integración en `MainWindow`, seguridad).

## [0.11.0] - 2026-07-15

Catálogo reutilizable de productos y perfiles de Loading Space
respaldado por SQLite/SQLAlchemy (fase 7.1): un usuario puede guardar
productos y perfiles de espacio para reutilizarlos en proyectos
futuros, y la aplicación lleva un historial básico de proyectos
abiertos/guardados y ejecuciones de optimización. Ver
`docs/Database.md` para el detalle completo.

### Added

- `infrastructure/database/`: `paths.py` (`get_user_database_path()`,
  por defecto `%LOCALAPPDATA%/CargoOptimizer3D/cargo_optimizer.db`,
  fuera del repositorio y nunca versionada), `exceptions.py`
  (`DatabaseError`/`DatabaseInitializationError`/
  `DatabaseMigrationError`/`RepositoryError`/
  `DuplicateCatalogSkuError`/`DuplicateLoadingSpaceProfileError`/
  `RecordNotFoundError`), `orm_models.py` (`ProductCatalogORM`,
  `LoadingSpaceProfileORM`, `ProjectHistoryORM`,
  `PackingRunHistoryORM`, `SchemaMetadataORM`, sin relaciones de clave
  foránea entre tablas), `migrations.py`
  (`initialize_database`/`migrate_database`, `schema_version = "1"`,
  versión desconocida = error claro, nunca adivinar), `engine.py`
  (`DatabaseManager`: sesiones cortas vía `session_scope()`,
  PRAGMAs `foreign_keys=ON`/`journal_mode=WAL`/`busy_timeout`, `backup()`
  vía la API nativa `sqlite3.Connection.backup`, `health_check()` que
  nunca lanza), `repositories.py` (`ProductCatalogRepository`,
  `LoadingSpaceProfileRepository`, `ProjectHistoryRepository`,
  `PackingRunHistoryRepository`, con conversión explícita ORM↔domain,
  borrado siempre lógico vía `is_active`, unicidad de SKU/nombre
  calculada solo entre registros activos), `catalog_service.py`
  (`CatalogService`: fachada única con los cuatro repositorios y
  `copy_to_project`/`copy_profile_to_project`, que siempre generan un
  `UUID` nuevo — una copia independiente, nunca ligada al catálogo).
- Perfiles de Loading Space integrados (`is_builtin=True`, protegidos
  contra modificación/archivado directo): contenedor 20', 40' y 40'
  High Cube, creados automáticamente si no existen
  (`ensure_builtin_profiles()`).
- UI: `presentation/desktop/dialogs/` (`ProductCatalogDialog`,
  `CatalogProductEditorDialog`, `LoadingSpaceProfilesDialog`,
  `LoadingSpaceProfileEditorDialog` — este último reutiliza
  `LoadingSpaceFormPanel` en vez de duplicar el formulario) y dos
  modelos de tabla de solo lectura
  (`ProductCatalogTableModel`/`LoadingSpaceProfileTableModel`).
  `MainWindow` gana acciones reales para abrir el catálogo, guardar un
  producto del proyecto en el catálogo, añadir productos del catálogo
  al proyecto, guardar el Loading Space actual como perfil y aplicar un
  perfil guardado.
- Registro automático de historial al abrir/guardar un `.cargo3d` y al
  finalizar una optimización correctamente; cualquier fallo de la base
  de datos durante el registro se degrada a un aviso en el panel de
  registro, sin interrumpir nunca la operación principal.
- **Modo limitado**: si SQLite no está disponible al iniciar, la
  aplicación abre igual con un aviso, las acciones de catálogo/perfiles
  quedan deshabilitadas y `.cargo3d` sigue funcionando sin ningún
  cambio.
- `pyproject.toml`: nueva dependencia `SQLAlchemy>=2.0,<3`.
- 116 pruebas nuevas (607 en total):
  `tests/infrastructure/database/` (base de datos, esquema, sesiones,
  PRAGMAs, backup, base de datos corrupta, repositorios de catálogo,
  perfiles e historial) y `tests/presentation/desktop/` (modelos de
  tabla, diálogos bajo `offscreen` sin abrir ventanas reales,
  integración completa en `MainWindow`, incluido modo limitado).
- `docs/Database.md` (esquema con diagrama Mermaid, versionado,
  repositorios, `CatalogService`, modo limitado, seguridad,
  diferencias con `.cargo3d`).

## [0.10.0] - 2026-07-15

Persistencia completa de proyectos en archivos `.cargo3d` (fase 7.0):
un usuario puede crear un proyecto, guardarlo, cerrar la aplicación y
reabrirlo días después para continuar exactamente donde lo dejó. Ver
`docs/ProjectFiles.md` para el formato completo.

### Added

- `infrastructure/persistence/`: `exceptions.py`
  (`ProjectFileError`/`ProjectFileNotFoundError`/
  `ProjectFileCorruptError`/`UnsupportedSchemaVersionError`/
  `ProjectFileWriteError`), `serialization.py` (traducción explícita
  campo a campo entre cada entidad de `domain` y un `dict` JSON-seguro,
  sin `pickle`/`jsonpickle`/`__dict__`), `project_file_repository.py`
  (`ProjectFileRepository.save`/`load`/`validate`/`backup`, escritura
  atómica vía archivo temporal + `os.replace`, backup automático de un
  nivel antes de sobrescribir, infraestructura de migración de
  `schema_version` con solo "1.0" implementada).
- Formato `.cargo3d`: JSON UTF-8 legible, con `format_name`,
  `schema_version`, `application_version`, `created_at` (conservado
  entre guardados sucesivos), `modified_at`, el `CargoProject`
  completo (espacio, todos los Load Units, último `PackingResult` con
  sus `Placement`/`UnpackedUnit`/avisos) y un `presentation_state`
  opaco para `infrastructure` (tema, splitters, docks visibles, si el
  resultado está desactualizado).
- `MainWindow`: ciclo de vida completo de proyecto — Nuevo, Abrir,
  Guardar, Guardar como, Cerrar proyecto, menú de Proyectos recientes
  (últimos 10, vía `QSettings`, elimina rutas inexistentes al abrir el
  menú), título con `*` cuando hay cambios sin guardar, confirmación
  Guardar/Descartar/Cancelar antes de cerrar la ventana o cambiar de
  proyecto con cambios pendientes, invalidación automática del
  resultado al modificar productos o espacio ("El resultado anterior
  fue invalidado porque el proyecto cambió.", sin volver a ejecutar el
  algoritmo), restauración completa al abrir (espacio, productos,
  resultado, panel de resultados, tabla de no cargados, avisos, visor
  3D, tema, disposición de paneles).
- `LoadingSpaceFormPanel.set_loading_space()` y señal `changed`;
  `ProductTableModel.set_load_units()`; `ResultsPanel.set_stale()`;
  `AppSettings.recent_project_files`/`add_recent_project_file`/
  `set_recent_project_files`.
- 48 pruebas nuevas: `tests/infrastructure/persistence/` (round-trip
  de serialización, round-trip completo de archivo, errores tipados,
  archivos corruptos, versión de esquema futura, backups, escritura
  atómica, `validate` sin reconstrucción completa) y
  `tests/presentation/desktop/test_main_window_project_persistence.py`
  (ciclo de vida completo en `MainWindow`). Nueva fixture `autouse` en
  `tests/presentation/desktop/conftest.py`
  (`_no_blocking_question_dialog`) que evita que cualquier prueba se
  cuelgue esperando un `QMessageBox.question` real bajo `offscreen`.
- `docs/ProjectFiles.md`, `examples/example_project.cargo3d` (generado
  con el propio `ProjectFileRepository`, no escrito a mano).

### Fixed

- `LoadingSpaceFormPanel.build_loading_space()` perdía el tipo de los
  enums `LoadingSpaceCategory`/`DoorPosition`: `QComboBox.currentData()`
  los devolvía como `str` planos (Qt aplana subclases de `str` como
  estos `StrEnum` al pasar por `QVariant`), lo cual era invisible hasta
  que la nueva serialización JSON necesitó `.value` por primera vez.
  Corregido reconstruyendo explícitamente el enum
  (`LoadingSpaceCategory(...)`/`DoorPosition(...)`) a partir del valor
  devuelto por Qt.

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
