# Automatización profesional del flujo Excel (fase 8.1)

Este documento describe la fase 8.1, que se apoya por completo en
`infrastructure/excel/` (fase 8.0, ver `docs/Excel.md`) sin añadir
ningún formato nuevo. El objetivo no es leer/escribir más tipos de
archivo: es reducir al mínimo el trabajo manual de quien ya importa
catálogos reales de logística — con sus propias cabeceras, su propio
orden de columnas, sus propios SKU repetidos — a CargoOptimizer3D.

## 1. Propósito y alcance

Cubre:

- Un **mapeador de columnas** que detecta automáticamente qué columna
  del archivo corresponde a qué campo del sistema, y deja asignar a
  mano las que no reconoce.
- **Perfiles de mapeo** reutilizables, guardados en el catálogo SQLite
  (fase 7.1): cuatro perfiles oficiales (Kupfer, Joan, Exanco, Formato
  estándar CargoOptimizer) más los que el usuario cree.
- Una **vista previa** de la importación (filas, columnas, nuevos,
  existentes, duplicados, inválidos) antes de escribir nada.
- **Importación parcial**: todas las filas, solo las seleccionadas,
  solo nuevas, solo actualizadas o solo válidas.
- **Resolución de duplicados** por SKU: Actualizar/Duplicar/Ignorar,
  fila a fila o "aplicar a todos".
- **Arrastrar y soltar** un `.xlsx` sobre `MainWindow` o sobre el
  diálogo de catálogo, con detección automática del tipo de archivo.
- **Importación masiva** de varios archivos en una sola operación, con
  un resumen final.
- Un **informe de importación** (filas leídas/importadas/actualizadas/
  duplicadas/ignoradas/con error, tiempo empleado), exportable a
  `.xlsx`.
- **Exportación avanzada** de un `PackingResult`: elegir qué hojas
  exportar, en qué orden, con qué nombre, y ocultar las vacías.

No cubre (fuera de alcance): nuevos formatos de archivo, reportes PDF,
ni ninguna integración con un ERP (fase 9).

## 2. Dependencias y arquitectura

Igual que en la fase 8.0, `infrastructure/excel` sigue dependiendo
únicamente de `domain`, nunca de `infrastructure/database` ni de
PySide6/Qt. Los perfiles de mapeo guardados
(`ImportMappingProfileRepository`, en `infrastructure/database`) se
leen siempre desde `presentation/desktop/main_window.py` y se pasan a
`infrastructure/excel` como un `Mapping[str, str]` plano — mismo patrón
de inyección que ya usaba `packing_list_importer.import_packing_list`
con su `resolve_sku` callable. El contenido de los cuatro perfiles
oficiales (los alias de columna, en texto literal) está duplicado
deliberadamente en `infrastructure/database/repositories.py`
(`_BUILTIN_MAPPING_PROFILES`) en vez de importarse desde
`infrastructure/excel` — evita que `infrastructure/database` dependa de
`infrastructure/excel`, y son datos, no lógica: cuatro tuplas
constantes que no requieren ninguna abstracción compartida.

```
infrastructure/excel/
├── mapping.py            Alias de columna, detección, hoja remapeada en memoria, import_*_with_mapping()
├── import_preview.py      CatalogImportPreview + build_catalog_preview()
├── import_plan.py         ImportPlan + build_import_plan() (selección parcial, duplicados)
├── import_report.py       ImportReport, BulkImportReport, build_import_report(), export_import_report()
└── advanced_export.py     SheetSelection, export_packing_result_advanced()

infrastructure/database/
└── repositories.py         ImportMappingProfileEntry, ImportMappingProfileRepository, perfiles integrados
                             ProductCatalogRepository.apply_bulk() (transacción única)

presentation/desktop/
├── drag_drop.py            has_excel_url()/first_excel_path()/all_excel_paths()
└── dialogs/
    ├── column_mapping_dialog.py       ColumnMappingDialog
    ├── duplicate_resolution_dialog.py DuplicateResolutionDialog
    ├── import_preview_dialog.py       ImportPreviewDialog
    └── bulk_import_dialog.py          BulkImportDialog
```

## 3. Mapeador de columnas (`mapping.py`)

Los importadores de la fase 8.0 (`iter_data_rows`, `require_headers`)
son estrictamente **posicionales**: la columna 1 del archivo debe ser
la columna 1 canónica, sin excepción. Eso es incompatible con un
archivo real de un cliente, que puede tener las columnas en cualquier
orden, con cualquier nombre y con columnas adicionales que no
interesan.

`mapping.py` resuelve esto con una capa de traducción, no reescribiendo
los importadores:

1. `detect_column_mapping(headers, target_kind)` compara cada cabecera
   del archivo (insensible a mayúsculas y espacios) contra un
   diccionario de alias conocidos (`CATALOG_COLUMN_ALIASES`,
   `PACKING_LIST_COLUMN_ALIASES`, `LOADING_SPACE_COLUMN_ALIASES`) y
   devuelve `(mapeo, no_reconocidas)`.
2. `build_remapped_worksheet(worksheet, mapeo, columnas_canonicas)`
   construye una hoja **nueva, en memoria** (`openpyxl.Workbook`
   nuevo), con las columnas reordenadas y renombradas a su nombre
   canónico; las columnas canónicas sin ninguna columna de origen
   asignada quedan en blanco.
3. Esa hoja remapeada se pasa a las funciones ya existentes
   `import_catalog_from_worksheet`/`import_packing_list_from_worksheet`/
   `import_loading_spaces_from_worksheet` (extraídas de
   `import_catalog`/`import_packing_list`/`import_loading_spaces` en
   esta misma fase, sin cambiar su lógica de fila) — el mapeo nunca
   duplica el bucle de conversión fila a fila.

Esto significa que un archivo con columnas *Código/Descripción/Peso
bruto* (Kupfer) se importa exactamente con las mismas reglas de
validación de dominio que un `CatalogTemplate.xlsx` oficial, sin ningún
código de importación nuevo aparte de la reordenación de columnas.

## 4. Perfiles de mapeo (`ImportMappingProfileRepository`)

Nueva tabla `import_mapping_profiles` en el catálogo SQLite (fase 7.1),
con el mismo patrón de borrado lógico (`is_active`) y protección de
perfiles integrados (`is_builtin`, no editables directamente — solo
duplicables) que ya usa `LoadingSpaceProfileRepository`. Cada perfil
guarda `name`, `target_kind` (`catalog`/`packing_list`/
`loading_space`), el mapeo completo (`column_mapping_json`),
`created_at` y `last_used_at` (actualizado por
`touch_last_used` cada vez que se aplica desde el asistente).

`CatalogService.create_default()` llama a
`import_mappings.ensure_builtin_profiles()`, que crea (si no existen
ya, comprobado por nombre) los cuatro perfiles oficiales:
**Kupfer**, **Joan**, **Exanco** y **Formato estándar
CargoOptimizer** (mapeo identidad de las 16 columnas de
`product_rows.PRODUCT_COLUMNS`). El usuario puede crear perfiles
nuevos desde `ColumnMappingDialog` ("Guardar como perfil…") en
cualquier importación de catálogo.

## 5. Vista previa y clasificación (`import_preview.py`)

`build_catalog_preview(result, resolve_sku, *, column_count)` recibe un
`CatalogImportResult` ya calculado (por `import_catalog_with_mapping` o
`import_catalog`) y lo clasifica sin escribir nada en el catálogo:

- **Nuevos** (`new_units`) / **existentes** (`existing_units`): según
  si `resolve_sku(unit.sku)` encuentra ya un producto — normalmente
  `CatalogService.products.get_by_sku`, mismo patrón de función
  inyectada que ya usaba `packing_list_importer`.
- **Duplicados** (`duplicate_errors`) / **inválidos**
  (`invalid_errors`): los `RowError` que ya genera el importador de la
  fase 8.0 se separan por si su mensaje contiene la palabra
  "duplicado" — reutiliza el texto de error ya informativo de la fase
  8.0 en vez de añadir un campo de clasificación nuevo a `RowError`.

`ImportPreviewDialog` muestra estos seis contadores (filas, columnas,
nuevos, existentes, duplicados, inválidos) y dos secciones más antes de
escribir nada: la lista de errores de fila (si los hay) y el
selector del modo de importación parcial.

## 6. Importación parcial y resolución de duplicados (`import_plan.py`)

`build_import_plan(preview, resolve_sku, *, selection_mode,
selected_skus, duplicate_resolutions, default_duplicate_resolution)`
es una función **pura** — no escribe nada — que produce un `ImportPlan`
(`to_add`, `to_update`, `ignored_skus`) combinando:

- `selection_mode`: `"all"` | `"selected"` | `"new_only"` |
  `"updated_only"` | `"valid_only"` (los cinco modos de la sección 5 de
  la especificación de fase). `"selected"` filtra por
  `selected_skus`, marcados en `ImportPreviewDialog`.
- `duplicate_resolutions: {sku: "update" | "duplicate" | "ignore"}` —
  cualquier SKU existente sin entrada explícita usa
  `default_duplicate_resolution` (por defecto `"update"`), lo que
  permite implementar "aplicar a todos" con un solo valor en vez de un
  mapa completo por fila. **Duplicar** genera un `LoadUnit` nuevo (UUID
  nuevo, SKU con el sufijo `-DUP`) en vez de sobrescribir; **Ignorar**
  añade el SKU a `ignored_skus` sin tocar el catálogo.

`DuplicateResolutionDialog` es la UI de esta sección: una fila por SKU
existente, un desplegable Actualizar/Duplicar/Ignorar por fila, y
"Aplicar a todos" para fijar la misma acción en bloque. Cancelar aborta
toda la importación — nunca se aplica un plan parcial sin que el
usuario haya decidido explícitamente cada duplicado (o el valor por
defecto, en importación masiva no interactiva).

## 7. Escritura transaccional (`ProductCatalogRepository.apply_bulk`)

`apply_bulk(*, to_add=(), to_update=())` abre **una única**
`session_scope()` para todo el lote: cualquier fallo (SKU duplicado
entre lo que se añade, un `id` de actualización que ya no existe)
propaga la excepción fuera del `with`, y `session_scope` hace
`rollback()` — ninguna fila del lote queda escrita si una sola falla.
Es el único punto de escritura real de un `ImportPlan`; todo lo demás
en `import_plan.py`/`import_preview.py` es cálculo puro sin efectos
secundarios.

## 8. Arrastrar y soltar (`drag_drop.py`)

`has_excel_url`/`first_excel_path`/`all_excel_paths` centralizan la
detección de ".¿trae este evento al menos un `.xlsx` local?" — usada
igual por `MainWindow.dragEnterEvent`/`dropEvent` y por
`ProductCatalogDialog.dragEnterEvent`/`dropEvent` (con
`setAcceptDrops` condicionado a que se le pase un callback
`on_excel_dropped`).

- Soltar sobre **`MainWindow`** despacha con la misma lógica que
  "Archivo > Importar Excel" (`detect_template_kind`): un archivo con
  forma de catálogo/packing list/espacio de carga se añade al
  **proyecto abierto**. Un archivo que no coincide con ninguna
  plantilla oficial pero sí tiene columnas reconocibles por alias
  (`detect_column_mapping`) abre `ColumnMappingDialog` y, tras
  aceptar, añade los productos mapeados al proyecto — nunca al
  catálogo SQLite, mismo destino que el resto de la ruta genérica de
  importación.
- Soltar sobre **`ProductCatalogDialog`** siempre pasa por el flujo
  completo de importación inteligente
  (`MainWindow._run_smart_catalog_import`, interactivo) y escribe en el
  **catálogo SQLite**; al terminar, el diálogo se refresca
  (`ProductCatalogDialog.refresh()`) sin cerrarse.
- Soltar varios archivos a la vez (`all_excel_paths`) los procesa uno
  tras otro con la misma lógica que si se soltaran por separado.

## 9. Importación masiva (`BulkImportDialog`)

Recibe un único `import_one: Callable[[Path], ImportReport]` inyectado
desde `MainWindow` — la misma función
(`_bulk_import_one_catalog_file`, que llama a `_run_smart_catalog_import`
con `interactive=False`) que ya usa el resto del flujo, solo que sin
ningún diálogo intermedio: mapeo automático por alias, todas las filas,
"Actualizar" como resolución por defecto para cualquier SKU existente.
Un archivo que falla (`ExcelError`, ej. corrupto) se reporta con
`QMessageBox.warning` y con un `ImportReport` vacío en el resumen; el
resto de archivos seleccionados se sigue importando. Al final se
muestra una tabla resumen (una fila por archivo) y un botón para
guardar ese resumen como `.xlsx`.

## 10. Informe de importación (`import_report.py`)

`ImportReport` (un archivo) y `BulkImportReport` (varios, con
propiedades `total_*` que suman) se combinan a partir de una
`CatalogImportPreview` ya calculada y un `ImportPlan` ya aplicado —
nunca recalculan nada por su cuenta. `export_import_report(report,
path)` escribe dos hojas (**Resumen**, con una fila de totales cuando
hay más de un informe; **Errores**, una fila por cada `RowError` con el
nombre del archivo de origen) con el mismo formato profesional
(`styles.py`) del resto del módulo, guardado siempre con
`save_workbook_atomic`.

## 11. Exportación avanzada (`advanced_export.py`)

`export_packing_result_advanced(result, load_units_by_id, path, *,
application_version, sheet_selections=None, hide_empty_sheets=False)`
construye el mismo libro de cinco hojas que `export_packing_result`
(vía `build_packing_result_workbook`, extraída de `result_exporter.py`
en esta fase) y luego, sobre ese mismo `Workbook`, elimina las hojas no
elegidas, renombra las elegidas (`SheetSelection.display_name`) y fija
su orden. `openpyxl` no expone una API pública para reordenar todas las
hojas de una vez (solo `move_sheet`, un desplazamiento relativo) — se
manipula directamente `workbook._sheets` (con un comentario explicativo
y un `# type: ignore[attr-defined]`, ya que mypy no conoce ese atributo
privado). `is_sheet_empty` marca **Productos no cargados** y
**Warnings** como vacíos cuando no tienen filas; **Resumen** y **Datos
del espacio** nunca se consideran vacíos. Lanza `ExcelError` si, tras
filtrar, no queda ninguna hoja.

Esta capacidad no tiene un diálogo dedicado propio: la especificación
de esta fase pide explícitamente cuatro diálogos (Mapeo, Duplicados,
Resumen, Importación masiva), no cinco — introducir un quinto
"AdvancedExportDialog" habría sido alcance no solicitado.

## 12. Integración en `MainWindow`

| Menú | Acción | Handler | Diálogos que abre (si `interactive=True`) |
|---|---|---|---|
| Productos | Importar catálogo (Excel)… | `_on_import_catalog_excel` | Mapeo (solo si hay columnas sin reconocer) → Vista previa → Duplicados (si hay SKU existentes) |
| Productos | Importar con mapeo de columnas… | `_on_import_catalog_excel_with_mapping` | Mapeo siempre → Vista previa → Duplicados |
| Productos | Importación masiva de Excel… | `_on_bulk_import_catalog_excel` | `BulkImportDialog` (sin diálogos intermedios por archivo) |

Las tres acciones nuevas comparten `_run_smart_catalog_import(path, *,
interactive, force_mapping_dialog=False)`, el único punto que orquesta
mapeo → vista previa → duplicados → `apply_bulk`. Cancelar en
cualquier paso interactivo devuelve `None` sin haber tocado el
catálogo. Las tres se deshabilitan en modo limitado
(`catalog_service is None`), igual que el resto de acciones
dependientes del catálogo SQLite (`_apply_catalog_availability` y el
bloque de `_set_running_controls_enabled` que las fuerza a `False`
mientras el optimizador está corriendo).

`MainWindow.setAcceptDrops(True)` y sus `dragEnterEvent`/`dropEvent`
despachan a `_handle_dropped_excel_file`, reutilizando
`detect_template_kind` (igual que "Archivo > Importar Excel", fase
8.0) con `_handle_unrecognized_dropped_file` como último recurso antes
de rendirse (sección 8 de este documento).

## 13. Pruebas

- `tests/infrastructure/excel/test_mapping.py` — detección de alias
  (Kupfer/Joan/Exanco-style), cabeceras no reconocidas, hoja remapeada
  (orden, columnas en blanco sin mapear), importación con mapeo para
  catálogo/packing list/loading space.
- `tests/infrastructure/excel/test_import_preview_plan.py` —
  clasificación nuevo/existente/duplicado/inválido, los cinco modos de
  importación parcial, las tres resoluciones de duplicado,
  "aplicar a todos".
- `tests/infrastructure/excel/test_import_report.py` — informe
  individual, totales agregados de `BulkImportReport`, exportación con
  hoja de errores y fila de totales.
- `tests/infrastructure/excel/test_advanced_export.py` — orden por
  defecto, reordenar/renombrar, ocultar hojas vacías, error si no queda
  ninguna hoja.
- `tests/infrastructure/database/test_import_mapping_profile_repository.py`
  — CRUD, los cuatro perfiles integrados (creación idempotente,
  protegidos contra edición directa), archivado/restauración,
  duplicado.
- `tests/infrastructure/database/test_product_catalog_repository.py`
  (ampliado) — `apply_bulk` transaccional: éxito combinado
  add+update, todo-o-nada ante SKU duplicado o `id` de actualización
  inexistente.
- `tests/presentation/desktop/test_column_mapping_dialog.py`,
  `test_duplicate_resolution_dialog.py`,
  `test_import_preview_dialog.py`, `test_bulk_import_dialog.py` — los
  cuatro diálogos nuevos, sin abrir nunca un `.exec()` real.
- `tests/presentation/desktop/test_drag_drop.py` — detección de
  `.xlsx` local en un evento de arrastre, con un doble ligero en vez de
  un `QDropEvent` real.
- `tests/presentation/desktop/test_main_window_excel_automation.py` —
  el flujo completo en `MainWindow`: mapeo automático y forzado,
  cancelar en cada paso, importación parcial, las tres resoluciones de
  duplicado, importación masiva no interactiva, arrastrar y soltar
  sobre `MainWindow` (catálogo/packing list/espacio de carga/archivo
  aliasable/archivo no reconocido) y sobre `ProductCatalogDialog`.

Precaución de prueba documentada aquí porque costó diagnosticar: bajo
`QT_QPA_PLATFORM=offscreen`, cualquier `QDialog.exec()` o
`QMessageBox.*` real que no se sustituya por un doble se queda
esperando un clic que nunca llega — **cuelga el proceso de pytest sin
ningún mensaje de error**, no lanza una excepción. Como esta fase
introduce diálogos nuevos en medio de una ruta que antes no abría
ninguno (`_on_import_catalog_excel`, que en la fase 8.0 escribía
directamente sin pedir confirmación), las pruebas de la fase 8.0 que
llamaban a esa ruta tuvieron que actualizarse para sustituir también
`ImportPreviewDialog`/`DuplicateResolutionDialog` — no solo
`QFileDialog`/`QMessageBox` como antes.

## 14. Seguridad

Ninguna regla nueva respecto a `docs/Excel.md`, sección 12: el mapeo de
columnas nunca ejecuta contenido de una celda, y `build_remapped_worksheet`
solo copia valores de celda entre hojas en memoria — sin fórmulas, sin
macros. La escritura del catálogo sigue pasando siempre por SQLAlchemy
con parámetros (`apply_bulk` incluido), nunca por interpolación de
texto.
