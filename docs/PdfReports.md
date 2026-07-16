# Informes PDF profesionales (`infrastructure/pdf/`, fase 9.1)

Este documento describe la implementación real del sistema de informes
PDF, diseñado en la fase 9.0 (`docs/PdfReportDesign.md`, ADR-0012) e
implementado exactamente según ese diseño en esta fase. No se
reabrieron decisiones de arquitectura: este documento reemplaza al de
diseño como referencia de "cómo funciona hoy"; el de diseño se conserva
como historial de las alternativas evaluadas y la revisión crítica.

## 1. Propósito y alcance

Un `PackingResult` ya calculado puede exportarse como uno de cinco
informes PDF distintos — desde un resumen ejecutivo de una página hasta
un informe técnico completo — con marca de la empresa, datos de
cliente, y opcionalmente una captura del visor 3D. Cubre:

- Los cinco tipos de informe oficiales (sección 4).
- Configuración de empresa/cliente/idioma/colores/cabecera/pie/marca de
  agua (sección 5).
- Integración opcional con la captura del visor 3D (sección 6).
- Una acción real en `MainWindow` ("Archivo > Exportar PDF…", sección
  10).

No cubre (fuera de alcance de esta fase, ver `docs/PdfReportDesign.md`,
sección 8): plantillas guardadas por el usuario, un segundo idioma
real (el campo existe, el diccionario de etiquetas en inglés no),
generación de informes sin ninguna ventana abierta, ni un editor visual
de plantillas.

## 2. Dependencias y arquitectura

`infrastructure/pdf` depende únicamente de `domain` y de `reportlab`
(dependencia de terceros nueva de esta fase) — nunca de `optimization`,
`presentation`, `infrastructure/excel` ni `infrastructure/database`,
verificado por `import-linter` igual que el resto de `infrastructure`.

```
infrastructure/pdf/
├── exceptions.py        PdfError, PdfConfigError, PdfRenderError
├── styles.py             Tipografía, colores, TableStyle compartidos (ningún import de domain)
├── layout.py              Cabecera, pie, numeración "Página X de Y", marca de agua (Canvas propio)
├── report_config.py       CompanyProfile, ClientInfo, ReportSection, ReportConfig — datos puros
├── report_content.py      ReportContent + build_report_content(): único punto que importa domain
├── sections.py            Una función por ReportSection — bloques de reportlab.platypus reutilizables
├── templates.py           ReportTemplate + los 5 informes oficiales como datos (ADR-0012)
└── report_builder.py       generate_report(): único módulo que importa reportlab.platypus
```

## 3. Módulos

- **`exceptions.py`**: `PdfError` (base), `PdfConfigError` (plantilla sin secciones o sin
  contenido — no debería ocurrir con los cinco informes oficiales), `PdfRenderError`
  (cualquier fallo de `reportlab` o de escritura de archivo, envuelto para que la interfaz nunca
  vea una excepción cruda de una biblioteca de terceros).
- **`styles.py`**: `build_stylesheet(accent_color_hex)` (títulos, subtítulos, cuerpo, texto
  atenuado, pie de página) y `table_style(accent_color_hex)` (cabecera de tabla con el color de
  acento, franjas de fila suaves) — fuentes estándar de PDF (Helvetica), sin fuentes embebidas.
- **`layout.py`**: `make_canvas_factory(config, content)` construye una subclase de
  `reportlab.pdfgen.canvas.Canvas` que guarda el estado de cada página (`showPage` sobrescrito) y
  dibuja cabecera/pie/marca de agua en una segunda pasada dentro de `save()`, cuando ya se conoce
  el número total de páginas — la técnica estándar de ReportLab para "Página X de Y". Un logo
  ausente o corrupto se ignora en silencio (`_draw_logo`, `try/except` que nunca propaga).
- **`report_config.py`**: `CompanyProfile` (nombre, logo, dirección, NIF, contacto, color de
  acento; `name` obligatorio, valida en `__post_init__`), `ClientInfo` (nombre, logo, contacto,
  referencia — todo opcional, efímero por informe), `ReportSection` (`StrEnum` con las nueve
  secciones reutilizables) y `ReportConfig` (empresa + cliente + idioma + color de acento +
  posición del logo de cabecera + `footer_text` con marcadores + `watermark_text` + tres banderas
  `show_*` que controlan el nivel de detalle compartido entre informes).
- **`report_content.py`**: `build_report_content(result, load_units_by_id, *, project_name,
  application_version, viewer_screenshot_png=None)` traduce un `PackingResult` ya calculado a
  `ReportContent` (todos los campos ya resueltos: SKU/nombre por SKU vía `load_units_by_id`,
  etiquetas de categoría/puerta/orientación en español — copias propias, independientes de
  `infrastructure/excel`, mismo criterio que evita el acoplo infra-a-infra ya aplicado en la fase
  8.1). `viewer_screenshot_png` se recibe ya capturado; esta función nunca genera ninguna imagen.
- **`sections.py`**: nueve funciones `build_*_section(content, config, stylesheet, ...)`, una por
  cada valor de `ReportSection` (además de `_safe_image`/`_label_value_table` como ayudas
  compartidas). Cada una devuelve una lista de *flowables* de `reportlab.platypus` — nunca escribe
  a un archivo ni conoce `ReportTemplate`.
- **`templates.py`**: `ReportTemplate` (`key`, `display_name`, `sections: tuple[ReportSection,
  ...]`, `config_overrides: Callable[[ReportConfig], ReportConfig]`, `is_builtin`) y las cinco
  constantes oficiales (`EXECUTIVE_SUMMARY`, `TECHNICAL_FULL`, `PACKING_LIST`,
  `INTERNAL_DIAGNOSTIC`, `CLIENT_REPORT`) agrupadas en `BUILTIN_TEMPLATES`;
  `get_template_by_key(key)` las busca por clave.
- **`report_builder.py`**: `generate_report(content, template, config, path)` — aplica
  `template.config_overrides`, construye la hoja de estilos, recorre `template.sections`
  despachando cada una a su función de `sections.py`, y llama a
  `SimpleDocTemplate.build(story, canvasmaker=make_canvas_factory(...))`. Escritura siempre
  atómica: archivo temporal en el mismo directorio + `os.replace` (mismo patrón que
  `save_workbook_atomic`/`ProjectFileRepository.save`).

## 4. Los cinco tipos de informe

| Informe (`key`) | Secciones incluidas (`ReportTemplate.sections`) | `config_overrides` |
|---|---|---|
| Resumen ejecutivo (`executive_summary`) | Portada, resumen ejecutivo, imagen del visor, datos del espacio | Ninguno |
| Informe técnico completo (`technical_full`) | Portada, resumen ejecutivo, imagen del visor, datos del espacio, productos cargados, productos no cargados, avisos, apéndice técnico | Ninguno |
| Packing list optimizado (`packing_list`) | Portada, productos cargados | Ninguno |
| Informe interno de diagnóstico (`internal_diagnostic`) | Portada, resumen ejecutivo, datos del espacio, productos cargados, productos no cargados, avisos, apéndice técnico | Marca de agua fija `"USO INTERNO — NO DISTRIBUIR"` |
| Informe para cliente (`client_report`) | Portada, resumen ejecutivo, imagen del visor, datos del espacio, productos cargados, productos no cargados, pie legal | Oculta columnas de posición, algoritmo/tiempo de ejecución y detalle de motivos de no-carga |

Detalle de contenido por sección (`sections.py`):

- **Portada**: logo de empresa (si existe y es legible), nombre del proyecto, título del informe,
  empresa, cliente/referencia (si hay `ClientInfo`), fecha de generación.
- **Resumen ejecutivo**: unidades solicitadas/cargadas/no cargadas, porcentaje completado,
  porcentaje de volumen utilizado, porcentaje de peso utilizado (o "Sin límite declarado"); si
  `show_algorithm_details` es `True` (por defecto, salvo informe de cliente), añade algoritmo
  utilizado y tiempo de ejecución.
- **Imagen del visor 3D**: se omite por completo si `viewer_screenshot_png is None` o si la imagen
  no se puede decodificar — nunca produce un error ni dibuja un hueco visible.
- **Datos del espacio**: nombre, categoría, dimensiones internas, peso máximo (o "Sin límite
  declarado"), posición de puerta, notas (si las hay).
- **Productos cargados**: tabla ordenada por orden de carga (`sequence_number`); columnas completas
  (SKU, nombre, posición X/Y/Z, orientación, dimensiones) si `show_position_columns` es `True`, o
  solo orden/SKU/nombre si es `False` (informe de cliente). "No hay productos cargados." si la
  lista está vacía.
- **Productos no cargados**: tabla completa con código y mensaje de motivo si
  `show_unpacked_details` es `True`, o un recuento más la lista de motivos únicos en lenguaje llano
  (sin código) si es `False`. "Todos los productos solicitados se cargaron correctamente." si no
  hay ninguno.
- **Avisos**: una línea por `PackingResult.warnings`; la sección se omite por completo si no hay
  ninguno.
- **Apéndice técnico**: algoritmo utilizado, tiempo de ejecución, versión de CargoOptimizer3D.
- **Pie legal**: un párrafo genérico (solo en el informe de cliente) indicando que el documento se
  generó automáticamente a partir de un cálculo de optimización.

## 5. Configuración

`ReportConfig` se construye siempre con un `CompanyProfile` obligatorio (el resto de campos tienen
valores por defecto razonables). `MainWindow` construye hoy un `CompanyProfile(name="CargoOptimizer3D")`
mínimo sin persistencia — guardar un perfil de empresa reutilizable entre sesiones queda para una
fase posterior (`docs/PdfReportDesign.md`, sección 8, ya propone reutilizar el patrón de
`ImportMappingProfileRepository` para esto). `ClientInfo` se puede pasar por informe si se necesita
(no expuesto todavía en la UI de `MainWindow`, que genera con cliente vacío).

| Eje | Campo | Notas |
|---|---|---|
| Logo | `CompanyProfile.logo_path` / `ClientInfo.logo_path` | Ruta a imagen; ausente o corrupta se ignora sin error, tanto en la portada (`sections.py`) como en la cabecera de página (`layout.py`). |
| Idioma | `ReportConfig.locale` | Solo `"es"` implementado y probado en esta fase. |
| Color de acento | `ReportConfig.accent_color_hex` (o el de `company` si es `None`) | Un único color de acento (cabeceras de tabla, títulos). |
| Cabecera | `ReportConfig.header_logo_position` (`"left"`/`"right"`/`"center"`) | Logo de empresa en cada página, dibujado por `layout.py`. |
| Pie de página | `ReportConfig.footer_text` | Marcadores `{company}`, `{date}`, `{page}`, `{pages}` — sustitución literal, nunca `eval`/plantillas dinámicas. |
| Numeración | Automática | "Página X de Y" vía `layout.make_canvas_factory` (segunda pasada del `Canvas`). |
| Marca de agua | `ReportConfig.watermark_text` | `None` por defecto; fija para el informe de diagnóstico (`templates.py`). |

## 6. Integración con el visor 3D

`presentation/desktop/viewer/` gana, en esta fase, la única pieza de captura que le faltaba:

- `SceneController.export_screenshot_png() -> bytes | None` (en `scene_controller.py`): escribe
  con `Plotter.screenshot(path)` a un archivo temporal, lee los bytes de vuelta y lo borra —
  evita que `viewer/` dependa directamente de Pillow/imageio para codificar PNG él mismo.
- `Packing3DViewer.export_screenshot_png() -> bytes | None` (en `widget.py`): `None` si el visor
  no está disponible (modo de repuesto); delega en el controlador si lo está.

`MainWindow._on_export_pdf` llama a `self.viewer_widget.export_screenshot_png()` y pasa el
resultado (posiblemente `None`) a `build_report_content(..., viewer_screenshot_png=...)` —
`infrastructure/pdf` nunca importa PyVista ni `presentation.desktop.viewer`, exactamente como
diseñó ADR-0012.

## 7. Sistema de plantillas

Los cinco informes oficiales son instancias de datos de `ReportTemplate` (sección 3), no clases
distintas. `config_overrides` es una función `ReportConfig -> ReportConfig` (identidad por
defecto); `INTERNAL_DIAGNOSTIC` y `CLIENT_REPORT` la sustituyen por una que aplica
`dataclasses.replace(config, ...)`. Añadir un sexto informe es declarar una sexta constante, no
escribir código nuevo en `sections.py`/`report_builder.py`.

## 8. Escritura atómica y manejo de errores

`generate_report` escribe siempre a un archivo temporal (`tempfile.mkstemp(suffix=".pdf.tmp",
dir=path.parent)`) y solo hace `os.replace(tmp_path, path)` al terminar con éxito; cualquier
excepción durante `doc.build(...)` borra el temporal y se relanza como `PdfRenderError` — un corte
a mitad de generación nunca deja un `.pdf` corrupto en la ruta final. `PdfConfigError` se lanza si
una plantilla no tiene secciones o no genera ningún *flowable* (nunca ocurre con los cinco informes
oficiales; relevante solo si en el futuro se permiten plantillas personalizadas vacías).

## 9. Integración en `MainWindow`

| Menú | Acción | Handler |
|---|---|---|
| Archivo | Exportar &PDF… | `_on_export_pdf` |

`_on_export_pdf`:

1. Avisa y no hace nada si no hay `self._last_result` (igual criterio que "Exportar Excel…
   resultado").
2. Pregunta el tipo de informe con `QInputDialog.getItem` sobre los `display_name` de
   `BUILTIN_TEMPLATES` (mismo patrón que "Exportar Excel…" al elegir Catálogo/Resultado).
3. Pide carpeta y nombre con `QFileDialog.getSaveFileName` (`_prompt_save_pdf_path`, añade `.pdf`
   si falta — mismo patrón que `_prompt_save_excel_path`).
4. Construye `ReportContent` con `self._last_load_units_by_id`, el nombre de proyecto
   (`_project_display_name()`) y la captura del visor si está disponible.
5. Llama a `generate_report`; cualquier `PdfError` se muestra con `QMessageBox.critical`, nunca se
   pierde en silencio.

La acción se deshabilita mientras una optimización está en curso (mismo criterio que "Exportar
Excel… resultado", ya que ambas dependen de `self._last_result`).

## 10. Seguridad

Mismo criterio que `infrastructure/excel` (`docs/Excel.md`, sección 12): ninguna ruta de archivo se
construye a partir de texto de usuario sin pasar por `pathlib.Path`; `footer_text` solo sustituye
un conjunto cerrado de marcadores conocidos (nunca `eval`/plantillas dinámicas tipo Jinja2);
ninguna celda de un PDF ejecuta código.

## 11. Pruebas

`tests/infrastructure/pdf/` cubre: los cinco tipos de informe oficiales (parametrizado sobre
`BUILTIN_TEMPLATES`), con y sin imagen del visor (incluida una imagen corrupta, que nunca debe
romper la generación), con logo existente y con logo ausente, proyecto vacío y proyecto completo,
`config_overrides` de cada plantilla (marca de agua forzada, columnas ocultas), numeración
"Página X de Y" en un documento de varias páginas, marca de agua presente/ausente según el
informe, escritura atómica (sin archivos temporales huérfanos), y el error de configuración cuando
una plantilla no tiene secciones. Validación con `pypdf` (parser independiente de `reportlab`, solo
dependencia de desarrollo): cuenta de páginas y texto extraído, nunca solo "el archivo existe".

`tests/presentation/desktop/test_main_window_pdf_export.py` cubre la acción completa en
`MainWindow` bajo `offscreen` (sin resultado, cancelar en cada paso, los cinco tipos de informe,
sufijo `.pdf` añadido automáticamente, deshabilitada durante una optimización).

## 12. Smoke test y limitaciones de verificación

Se ejecutó un smoke test real de principio a fin: un `CargoProject` real (contenedor 20', cuatro
tipos de producto, incluida maquinaria deliberadamente sobredimensionada para forzar unidades no
cargadas) optimizado con el motor real (`PackingEngine.optimize`, sin simular ni mockear nada),
seguido de la generación de los cinco informes oficiales y su validación con `pypdf` (páginas y
texto extraído correctos en los cinco). Este entorno de desarrollo no tiene forma de invocar
Adobe Acrobat o Microsoft Edge como aplicaciones de escritorio reales, y la navegación a `file://`
en el navegador embebido de este entorno fue bloqueada por su propio sandbox — no se pudo
completar una apertura visual literal en esas tres aplicaciones nombradas en el encargo. La
validación con `pypdf` (una biblioteca de lectura de PDF completamente independiente de
`reportlab`, que analiza la estructura real del archivo — objetos, flujo de contenido, fuentes) es
la verificación más rigurosa disponible en este entorno de que el PDF generado es válido y se
abriría correctamente en cualquier lector conforme al estándar. Se recomienda una verificación
manual puntual (abrir un informe generado con un doble clic) antes de considerar el flujo probado
en un entorno de usuario final real.
