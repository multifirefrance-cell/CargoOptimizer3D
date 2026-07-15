# Importación y exportación profesional de Excel (`.xlsx`, fase 8.0)

Este documento describe `infrastructure/excel/`: el módulo que integra
CargoOptimizer3D con Microsoft Excel dentro del flujo de trabajo real
de logística — importar catálogos, packing lists y perfiles de espacio
de carga, y exportar catálogos y resultados de optimización con
formato profesional.

## 1. Propósito y alcance

El objetivo no es "abrir hojas Excel": es que un usuario que ya
gestiona sus productos, packing lists y espacios de carga en Excel
pueda seguir haciéndolo, y que CargoOptimizer3D lea y escriba
exactamente el formato que ese flujo de trabajo espera.

Cubre:

- Importar un **catálogo** completo de productos (`LoadUnit`).
- Importar un **Packing List** (SKU + Cantidad), resolviendo cada SKU
  contra el catálogo SQLite (fase 7.1).
- Importar perfiles de **Loading Space** (contenedores, camiones,
  vans, bodegas, espacios personalizados).
- Exportar el catálogo a `.xlsx`.
- Exportar un `PackingResult` completo (resumen, productos cargados,
  productos no cargados, avisos, datos del espacio).

No cubre (fuera de alcance de esta fase): reportes PDF, exportar
Loading Space individualmente, importar/exportar históricos, ni
ninguna integración con un ERP (eso es la fase 9).

## 2. Dependencias y arquitectura

`infrastructure/excel` depende únicamente de `domain` — nunca de
`optimization`, `presentation` ni de PySide6/Qt. Igual que
`infrastructure/persistence` (fase 7.0) e `infrastructure/database`
(fase 7.1), es un adaptador de infraestructura desacoplado: no importa
`CatalogService` ni SQLAlchemy directamente. El importador de Packing
List recibe un `resolve_sku: Callable[[str], LoadUnit | None]` que
`presentation/desktop/main_window.py` conecta a
`CatalogService.products.get_by_sku` — el mismo patrón de inyección de
una función en vez de una dependencia concreta que ya usa
`PackingStrategy` como `Protocol` en `optimization`.

Usa exclusivamente [`openpyxl`](https://openpyxl.readthedocs.io/):
nunca `pandas`, `xlrd` ni CSV como sustituto. Sin macros, sin VBA — solo
estilos y tablas nativas de `.xlsx`.

```
infrastructure/excel/
├── exceptions.py           ExcelError, ExcelFileError, ExcelTemplateError
├── row_parsing.py          Ayudas genéricas de parseo (blanco, booleano, número, etiqueta de enum)
├── results.py              RowError, CatalogImportResult, LoadingSpaceImportResult, PackingListImportResult
├── styles.py                Formato compartido: cabeceras, bordes, tablas, autoajuste de columnas
├── workbook_utils.py        Apertura segura, cabeceras, iteración de filas, escritura atómica
├── product_rows.py          Esquema de columnas de LoadUnit (catálogo)
├── loading_space_rows.py    Esquema de columnas de LoadingSpace
├── catalog_importer.py      import_catalog()
├── catalog_exporter.py      export_catalog()
├── packing_list_importer.py import_packing_list()
├── loading_space_importer.py import_loading_spaces()
├── result_exporter.py       export_packing_result()
├── detection.py             detect_template_kind() — identifica qué plantilla es un archivo por sus cabeceras
└── templates.py             Generación de las cuatro plantillas oficiales
```

## 3. Nunca importar una fila inválida en silencio

Cada importador valida **fila a fila** contra el constructor de
dominio correspondiente (`LoadUnit`, `LoadingSpace`) — nunca reimplementa
sus invariantes. El resultado de cualquier importación es siempre un
objeto `*ImportResult` con dos partes:

- Las entidades reconstruidas correctamente (`units`/`spaces`/`resolved_units`).
- `errors: tuple[RowError, ...]` — una entrada por cada fila que no se
  pudo importar, con su número de fila (tal como lo vería un usuario
  en Excel, cabecera incluida) y un mensaje claro.

Nunca se lanza una excepción por una fila individual inválida: eso
detendría la importación completa de un archivo con 500 filas por un
solo error de tecleo. En su lugar, `MainWindow` siempre muestra los
errores de fila en un `QMessageBox.warning` — nunca los descarta ni
los deja solo en el registro.

Solo se lanza una excepción (`ExcelFileError`/`ExcelTemplateError`)
cuando el archivo **completo** no se puede procesar: corrupto, no es
un `.xlsx` válido, o no tiene las cabeceras esperadas.

## 4. Esquema de columnas del catálogo (`product_rows.py`)

| Columna | Campo de `LoadUnit` | Notas |
|---|---|---|
| SKU | `sku` | Obligatorio, único dentro del archivo |
| Nombre | `name` | Obligatorio |
| Largo/Ancho/Alto (cm) | `dimensions` | Obligatorios, > 0 |
| Peso (kg) | `weight_kg` | Obligatorio, >= 0 |
| Cantidad | `quantity` | Por defecto 1 |
| Color | `color_hex` | Por defecto `#CCCCCC` si está vacío |
| Fragil | `fragile` | "Si"/"No", por defecto "No" |
| Tipo de empaque | `package_type` | Etiqueta en español o valor interno del enum; por defecto Individual |
| Extintor | `is_extinguisher` | "Si"/"No" |
| Agente | `extinguisher_agent` | Obligatorio si Extintor = Si |
| Peso nominal (kg) | `extinguisher_nominal_kg` | Obligatorio si Extintor = Si |
| Apilamiento | `max_stack_count` | Por defecto 1 |
| Orientaciones | `allowed_orientation_codes` | Lista separada por comas, o "Todas" (por defecto) |
| Notas | `notes` | Opcional |

Las celdas de enum (Tipo de empaque, Agente, Orientaciones) aceptan
tanto la etiqueta en español como el valor interno estable del enum
(`grouped_box`, `co2`, `lwh_xyz`, etc.), insensible a mayúsculas.

## 5. Packing List (`packing_list_importer.py`)

Columnas: **SKU**, **Cantidad**. Cada SKU se resuelve contra el
catálogo mediante `resolve_sku`. Un mismo SKU repetido en varias filas
**suma sus cantidades** en vez de tratarse como error — a diferencia
del catálogo, un packing list con líneas de picking repetidas para el
mismo artículo es una situación normal en logística.

Los SKU que no se encuentran en el catálogo se devuelven en
`missing_skus`, nunca causan una excepción: `MainWindow` muestra un
diálogo con la lista completa de SKU faltantes y dos opciones,
**Continuar** (importa solo lo encontrado) o **Cancelar** (no importa
nada).

## 6. Loading Space (`loading_space_importer.py`)

Columnas: Nombre, Categoria, Largo/Ancho/Alto (cm), Peso maximo (kg),
Posicion de puerta, Notas. Cubre cualquier espacio de carga universal
(contenedor, camión, van, bodega, espacio personalizado — ver
ADR-0002): `Categoria` es solo metadata descriptiva. Si el archivo
contiene un único espacio válido, se aplica directamente al formulario;
si contiene varios, `MainWindow` pregunta cuál aplicar.

## 7. Exportación de resultados (`result_exporter.py`)

`export_packing_result(result, load_units_by_id, path, *,
application_version)` escribe un único libro con cinco hojas:

1. **Resumen** — algoritmo utilizado, tiempo de ejecución, unidades
   solicitadas/cargadas/no cargadas, volumen usado (cm³ y m³) y su
   porcentaje, peso usado y su porcentaje (o "Sin límite declarado" si
   el espacio no declara peso máximo), número de avisos, versión de la
   aplicación y fecha de generación.
2. **Productos cargados** — una fila por `Placement`: SKU, nombre,
   número de instancia, posición X/Y/Z, orientación, dimensiones
   colocadas, orden de colocación.
3. **Productos no cargados** — una fila por `UnpackedUnit`: SKU,
   nombre, número de instancia, motivo y detalle.
4. **Warnings** — una fila por aviso de `PackingResult.warnings`.
5. **Datos del espacio** — nombre, categoría, dimensiones, volumen,
   peso máximo, posición de puerta, notas.

`load_units_by_id` se recibe junto al `PackingResult` para resolver
SKU/nombre — mismo patrón ya usado por `Packing3DViewer.display_result`
(fase 6.1) y `UnpackedUnitTableModel` (fase 5.1): evita ampliar
`PackingResult`/`Placement` con datos de `LoadUnit` que no les
corresponden.

## 8. Formato profesional (`styles.py`)

Cabeceras en negrita con relleno azul suave, bordes finos en toda la
zona de datos, autoajuste aproximado del ancho de columna (`openpyxl`
no soporta autoajuste nativo — se estima a partir del contenido más
largo de cada columna) y una tabla nativa de Excel
(`openpyxl.worksheet.table.Table`, estilo `TableStyleMedium9`, con
franjas de fila suaves) sobre cada rango de datos. Sin macros, sin VBA.

Toda escritura de archivo pasa por `save_workbook_atomic` en
`workbook_utils.py`: archivo temporal en el mismo directorio +
`os.replace` — mismo patrón que `ProjectFileRepository` (fase 7.0),
para que un corte a mitad de la escritura nunca deje un `.xlsx`
corrupto en la ruta final.

## 9. Plantillas oficiales (`templates.py`, `examples/templates/`)

Cuatro plantillas, generadas con el propio código de exportación del
paquete (nunca escritas a mano celda a celda) — igual que
`examples/example_project.cargo3d` se generó con el `ProjectFileRepository`
real en la fase 7.0:

- `CatalogTemplate.xlsx` — tres productos de ejemplo (caja individual
  frágil, pallet apilable, extintor).
- `PackingListTemplate.xlsx` — SKU/Cantidad de esos mismos tres
  productos, para que el ejemplo funcione de punta a punta.
- `LoadingSpaceTemplate.xlsx` — contenedor 20', contenedor 40' y una
  bodega personalizada sin límite de peso.
- `OptimizationResultTemplate.xlsx` — un `PackingResult` ilustrativo
  construido directamente con los constructores de `domain` (sin
  invocar `PackingEngine`: no hace falta ejecutar el optimizador real
  para mostrar el formato de la hoja de resultados), con las cinco
  hojas completas.

`generate_all_templates(directory, *, application_version)` regenera
las cuatro; se usó para producir los archivos versionados en
`examples/templates/`.

## 10. Detección automática (`detection.py`)

`detect_template_kind(path)` identifica si un `.xlsx` es un catálogo,
un packing list o un espacio de carga comparando su fila de cabecera
(insensible a mayúsculas/espacios) contra las tres plantillas
conocidas. Devuelve `None` si no coincide con ninguna — nunca adivina.
Lo usa la acción genérica "Archivo > Importar Excel" de `MainWindow`
para no obligar al usuario a decir de antemano qué tipo de archivo está
importando.

## 11. Integración en `MainWindow`

| Menú | Acción | Handler | Destino |
|---|---|---|---|
| Archivo | Importar Excel… | `_on_import_excel_auto` | Detecta el tipo y despacha a uno de los siguientes |
| Archivo | Exportar Excel… | `_on_export_excel_menu` | Pregunta Catálogo/Resultado y despacha |
| Productos | Importar productos… | `_on_import_excel_auto` | Mismo detector; un catálogo-Excel se añade al **proyecto actual** |
| Productos | Importar catálogo (Excel)… | `_on_import_catalog_excel` | Guarda en el **catálogo SQLite** (SKU existente → se omite con aviso, nunca se sobrescribe) |
| Productos | Exportar catálogo (Excel)… | `_on_export_catalog_excel` | Exporta `CatalogService.products.list_active()` |
| Espacio de carga | Importar desde Excel… | `_on_import_loading_space_excel` | Aplica el perfil al formulario |
| Proyecto | Importar Packing List… | `_on_import_packing_list_excel` | Resuelve contra el catálogo, añade al proyecto |
| Proyecto | Exportar resultado… | `_on_export_result_excel` | Exporta `self._last_result` (avisa si no hay resultado aún) |

Distinción importante: importar un archivo con forma de **catálogo**
desde "Archivo > Importar Excel" o "Productos > Importar productos"
añade los productos directamente al **proyecto abierto** (como
`LoadUnit` nuevos, con SKU duplicados frente al proyecto omitidos y
reportados); la acción específica "Productos > Importar catálogo
(Excel)" los guarda en el **catálogo SQLite** persistente. Son destinos
distintos a propósito — el mismo archivo `.xlsx` puede usarse para
ambos flujos sin conversión.

Las acciones que dependen del catálogo SQLite (`Importar/Exportar
catálogo (Excel)`, `Importar Packing List`) se deshabilitan en modo
limitado (`catalog_service is None`, ver `docs/Database.md`) mediante
`_apply_catalog_availability()`. Ninguna acción de Excel queda nunca
sin manejador conectado; los errores se muestran siempre con
`QMessageBox`, nunca solo por consola.

## 12. Seguridad

Nunca se ejecuta contenido de una celda como código (sin macros, sin
fórmulas evaluadas al leer — `load_workbook(..., data_only=True)` lee
el último valor calculado por Excel, no la fórmula). Ninguna ruta de
archivo ni nombre de hoja se construye a partir de texto de usuario sin
pasar por `pathlib.Path`. La apertura de cualquier archivo pasa siempre
por `open_workbook`, que traduce cualquier fallo de `openpyxl`/`zipfile`
a `ExcelFileError` — nunca se propaga una excepción cruda de una
biblioteca de terceros hasta la interfaz.

## 13. Pruebas

`tests/infrastructure/excel/` cubre: archivo corrupto, cabeceras
faltantes o en otro orden, tipos incorrectos (dimensión no numérica,
booleano irreconocible, tipo de empaque inválido), SKU inexistentes en
un Packing List, SKU duplicados (rechazados en catálogo, sumados en
Packing List), filas completamente vacías (se saltan), y round-trip
completo export→import para catálogo, espacios de carga y resultado —
incluidas las cuatro plantillas oficiales, que se auto-importan sin
errores como prueba de regresión. `tests/presentation/desktop/test_main_window_excel_integration.py`
cubre la integración completa en `MainWindow` bajo `offscreen` (detección
automática, ambos destinos de un catálogo-Excel, Packing List con
SKU faltantes en sus dos rutas, exportación de catálogo/resultado, modo
limitado), sin abrir nunca un diálogo real.
