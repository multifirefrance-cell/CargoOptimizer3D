# Diseño del sistema profesional de informes PDF (Fase 9.0)

Este documento es **exclusivamente de diseño**. No se implementa
ningún generador PDF en esta fase, no se añade `reportlab` como
dependencia y no se crea el paquete `infrastructure/pdf/` todavía — su
contenido se diseña aquí para que la fase 9.1 (implementación) pueda
empezar a escribir código directamente, sin decisiones de arquitectura
pendientes.

## Índice

1. [Objetivo y alcance](#1-objetivo-y-alcance)
2. [Arquitectura: `infrastructure/pdf/`](#2-arquitectura-infrastructurepdf)
3. [Los cinco tipos de informe](#3-los-cinco-tipos-de-informe)
4. [Contenido de cada informe](#4-contenido-de-cada-informe)
5. [Configuración](#5-configuración)
6. [Integración con el visor 3D](#6-integración-con-el-visor-3d)
7. [Sistema de plantillas](#7-sistema-de-plantillas)
8. [Personalización futura](#8-personalización-futura)
9. [Flujo de generación de extremo a extremo](#9-flujo-de-generación-de-extremo-a-extremo)
10. [Dependencias y regla de capas](#10-dependencias-y-regla-de-capas)
11. [Seguridad](#11-seguridad)
12. [Pruebas (diseño para la fase 9.1)](#12-pruebas-diseño-para-la-fase-91)
13. [Decisiones descartadas](#13-decisiones-descartadas)
14. [Revisión crítica](#14-revisión-crítica)

## 1. Objetivo y alcance

CargoOptimizer3D ya exporta un `PackingResult` a Excel con formato
profesional (fase 8.0, `docs/Excel.md`). Ese formato es correcto para
trabajar los datos (filtrar, ordenar, reutilizar en otra hoja), pero no
sustituye a un documento pensado para **leerse e imprimirse**: un
informe de una optimización que un cliente reciba por correo, que se
archive como evidencia de un cálculo, o que el propio equipo use para
diagnosticar un caso difícil.

El objetivo de esta fase es diseñar ese sistema de informes PDF: qué
tipos de informe existen, qué contienen, cómo se configuran (marca,
idioma, cliente), cómo se integran con el visor 3D, y cómo se permite
en el futuro que el usuario los personalice — sin escribir ni una
línea de `reportlab` todavía.

Fuera de alcance de esta fase (y de la 9.1, salvo que se decida
explícitamente): informes en otros idiomas más allá de español/inglés
preparados aquí como estructura; firma digital de PDF; envío por
correo del informe generado (eso es fase 10, integración ERP, si
aplica); un editor visual de plantillas (la personalización de la
sección 8 es programática/de datos, no un diseñador WYSIWYG).

## 2. Arquitectura: `infrastructure/pdf/`

```
infrastructure/pdf/
├── exceptions.py        PdfError y subclases tipadas
├── styles.py             Tipografía, colores, estilos de párrafo y tabla compartidos
├── layout.py              Cabecera/pie de página, numeración, marca de agua (callbacks de página)
├── report_config.py       CompanyProfile, ClientInfo, ReportSection, ReportConfig (datos puros)
├── report_content.py      ReportContent: PackingResult + CargoProject + LoadUnit -> datos neutrales
├── sections.py            Un bloque de contenido reutilizable por función (portada, resumen, tabla
│                          de cargados, tabla de no cargados, avisos, datos del espacio, cliente)
├── templates.py           ReportTemplate (orden de secciones) + los 5 informes oficiales como datos
└── report_builder.py       generate_report(...): el único módulo que importa reportlab directamente
```

Justificación de cada módulo (por qué existe, no solo qué hace):

- **`exceptions.py`**: mismo criterio que `infrastructure/excel/exceptions.py` — `PdfError` base y
  subclases tipadas (`PdfRenderError`, `PdfConfigError`) para que un fallo de generación nunca se
  propague como una excepción cruda de `reportlab` hasta la interfaz.
- **`styles.py`**: la tipografía/colores/estilos de tabla se comparten entre los cinco tipos de
  informe (todos usan la misma cabecera, el mismo estilo de tabla de productos, etc.); centralizarlo
  evita que cada informe reinvente su propio estilo, exactamente el papel que ya cumple
  `infrastructure/excel/styles.py`.
- **`layout.py`**: cabecera, pie de página, numeración ("Página X de Y") y marca de agua son
  *page callbacks* de ReportLab (`onFirstPage`/`onLaterPages`) — un concepto transversal a
  cualquier tipo de informe, no una decoración de un informe concreto. Aislarlo en su propio módulo
  permite probarlo una vez (¿la cabecera muestra el logo correcto? ¿la numeración es correcta con 1
  página, con 50?) sin repetir la prueba por cada tipo de informe.
- **`report_config.py`**: **datos puros, sin ningún import de `reportlab`** — `CompanyProfile`
  (nombre, logo, dirección, color de marca), `ClientInfo` (nombre, logo opcional, referencia),
  `ReportSection` (enum: portada, resumen ejecutivo, tabla de cargados, tabla de no cargados, avisos,
  datos del espacio, apéndice técnico, pie legal) y `ReportConfig` (idioma, colores, textos de
  cabecera/pie, si lleva marca de agua y su texto). Separarlo de `report_builder.py` permite que
  `presentation/desktop` construya y valide esta configuración (un formulario "Datos de la empresa")
  sin importar `reportlab` en ningún punto de `presentation`.
- **`report_content.py`**: el **único punto** que traduce `domain` (`PackingResult`, `CargoProject`,
  `LoadUnit`) a una estructura neutral de "qué hay que mostrar" (`ReportContent`, un dataclass con
  listas ya resueltas de filas de producto, ya con SKU/nombre resueltos vía un `Mapping[UUID,
  LoadUnit]` inyectado — mismo patrón que `load_units_by_id` en `viewer`/`result_exporter.py`).
  Ningún módulo de `sections.py`/`report_builder.py` toca `domain` directamente; todos reciben un
  `ReportContent` ya construido. Esto hace que cambiar de biblioteca de PDF en el futuro (si alguna
  vez fuera necesario) solo afecte a `report_builder.py`/`sections.py`, nunca a la traducción de
  dominio.
- **`sections.py`**: un bloque de contenido reutilizable por función (`build_cover_section`,
  `build_executive_summary_section`, `build_packed_table_section`, `build_unpacked_table_section`,
  `build_warnings_section`, `build_space_section`, `build_client_section`) que recibe `ReportContent`
  + `ReportConfig` y devuelve una lista de *flowables* de ReportLab. Los cinco tipos de informe
  (sección 3) son, literalmente, una selección y un orden distintos de estas mismas funciones — nunca
  hay una función "solo para el informe de cliente" que duplique la tabla de productos cargados ya
  escrita para el informe técnico.
- **`templates.py`**: `ReportTemplate` (nombre + tupla ordenada de `ReportSection` + overrides de
  `ReportConfig`, p. ej. el informe de diagnóstico fuerza marca de agua "USO INTERNO") y los cinco
  informes oficiales (sección 3) como instancias constantes de ese mismo tipo — mismo criterio que
  `_BUILTIN_MAPPING_PROFILES` en `infrastructure/database/repositories.py` (fase 8.1): datos, no
  lógica nueva por variante.
- **`report_builder.py`**: `generate_report(content, template, config, path)` — arma el documento
  (`reportlab.platypus.SimpleDocTemplate` o equivalente) recorriendo `template.sections`, llamando a
  la función de `sections.py` correspondiente a cada una, aplicando `layout.py` como *page callback* y
  `styles.py` para la tipografía. Es el único módulo de todo el paquete que importa
  `reportlab.platypus`/`reportlab.lib` — mismo aislamiento que `workbook_utils.py`/`styles.py` son los
  únicos puntos de `infrastructure/excel` que tocan `openpyxl` en profundidad.

Ningún módulo nuevo se propone más allá de estos ocho: no se separa, por ejemplo, un
`cover_page.py` por cada sección de `sections.py` (serían 7 módulos casi vacíos para una única
función cada uno) ni se crea una jerarquía de clases `ExecutiveSummaryReport`/`TechnicalReport` (la
sección 7 explica por qué un `ReportTemplate` de datos sustituye esa jerarquía sin perder nada).

## 3. Los cinco tipos de informe

| # | Informe | Audiencia | Extensión típica |
|---|---|---|---|
| 1 | Resumen ejecutivo | Quien decide, sin tiempo para el detalle | 1-2 páginas |
| 2 | Informe técnico completo | Ingeniería/logística propia, auditoría | Todas las que hagan falta |
| 3 | Packing List optimizado | Personal de almacén, ejecuta la carga física | Variable, pensado para imprimir en el muelle |
| 4 | Informe interno de diagnóstico | Soporte/desarrollo de CargoOptimizer3D | 2-4 páginas |
| 5 | Informe para cliente | Cliente final del usuario de CargoOptimizer3D | 2-3 páginas |

Los cinco comparten el mismo `ReportContent` (sección 2); lo que cambia es qué secciones
incluyen, en qué orden y con qué configuración (ver sección 4 para el detalle exacto, y la sección 7
para cómo esto se expresa como una única estructura de datos sin cinco clases distintas).

## 4. Contenido de cada informe

Matriz de secciones (✔ incluida, — no incluida) usando las mismas siete secciones de
`sections.py`:

| Sección | Ejecutivo | Técnico | Packing List | Diagnóstico | Cliente |
|---|---|---|---|---|---|
| Portada (nombre proyecto, cliente, fecha, logo) | ✔ | ✔ | ✔ | ✔ | ✔ |
| Resumen ejecutivo (% volumen, % peso, cargado/no cargado, algoritmo, tiempo) | ✔ (resumido) | ✔ | — | ✔ | ✔ (resumido, sin nombre del algoritmo) |
| Captura del visor 3D | ✔ (si disponible) | ✔ | — | opcional | ✔ (si disponible) |
| Datos del espacio (Loading Space: categoría, dimensiones, peso máx., posición de puerta) | resumido | ✔ | — | ✔ | resumido |
| Tabla de productos cargados (SKU, nombre, posición, orientación, orden de carga) | — | ✔ completa | ✔ completa, orden de carga destacado | ✔ completa | ✔ completa, sin columnas de posición X/Y/Z (solo orden) |
| Tabla de productos no cargados (SKU, motivo, detalle) | totales únicamente | ✔ completa | — | ✔ completa + código de motivo interno | totales + motivo en lenguaje llano |
| Avisos (`PackingResult.warnings`) | — | ✔ | — | ✔ | traducidos a lenguaje de cliente si aplica |
| Apéndice técnico (versión de CargoOptimizer3D, `algorithm_name`, `execution_time_seconds`, parámetros) | — | ✔ | — | ✔ (ampliado: código de la instancia, entorno) | — |
| Pie legal / condiciones | opcional | opcional | — | — | ✔ |
| Marca de agua | — | opcional ("BORRADOR") | — | **"USO INTERNO — NO DISTRIBUIR"** (fija) | opcional (marca del cliente) |

Notas de contenido importantes:

- El **Packing List optimizado** (informe 3) es deliberadamente el más corto y el más orientado a
  acción: una tabla ordenada por `sequence_number` (el mismo orden estable y determinista que ya usa
  el motor de optimización — ver `docs/OptimizationEngine.md`), pensada para que alguien en el muelle
  la siga físicamente sin tener que interpretar un resumen ejecutivo. No lleva captura del visor 3D
  a propósito: es un documento de ejecución, no de presentación.
- El **informe interno de diagnóstico** (informe 4) es el único que expone directamente los códigos
  de motivo (`UnpackedReason`, valores estables de `enum.StrEnum` — ver `docs/DomainModel.md`) sin
  traducir a texto para el cliente, y el único con marca de agua obligatoria — nunca opcional — para
  que sea visualmente imposible confundirlo con un documento apto para el cliente.
- El **informe para cliente** (informe 5) nunca expone `algorithm_name` ni
  `execution_time_seconds`: son detalles de implementación de CargoOptimizer3D, no información que un
  cliente final necesite o deba ver.
- Todos los informes muestran `weight_utilization_percent` como "Sin límite declarado" cuando
  `PackingResult.weight_utilization_percent is None` (mismo texto exacto que ya usa
  `result_exporter.py` en la fase 8.0) — consistencia de lenguaje entre Excel y PDF.

## 5. Configuración

Ocho ejes de configuración pedidos por el encargo, todos modelados como campos de
`CompanyProfile`/`ClientInfo`/`ReportConfig` (`report_config.py`, sección 2) — datos puros, nunca
lógica de renderizado:

| Eje | Dónde vive | Notas de diseño |
|---|---|---|
| Logo | `CompanyProfile.logo_path` / `ClientInfo.logo_path` | Ruta a un archivo de imagen (`.png`/`.jpg`); `report_builder.py` la resuelve con `reportlab.platypus.Image`, nunca se embebe como bytes en la configuración misma (igual que `LoadUnit.color_hex` es un valor de configuración, no un recurso). |
| Empresa | `CompanyProfile` (nombre, dirección, NIF/identificador fiscal, contacto, color de marca) | Configuración de la aplicación (una empresa no cambia de proyecto a proyecto) — ver sección 8 para dónde se persistiría en la fase 9.1. |
| Cliente | `ClientInfo` (nombre, logo opcional, contacto, referencia/nº de pedido) | Se introduce **por informe generado**, no es config de aplicación — un mismo usuario de CargoOptimizer3D genera informes para clientes distintos constantemente. |
| Idioma | `ReportConfig.locale: str` (`"es"` hoy; `"en"` preparado) | Mismo criterio que `product_rows.py`/`loading_space_rows.py`: un diccionario de etiquetas por idioma (`_LABELS_ES`, `_LABELS_EN`), nunca cadenas repetidas por toda la base de código. Hoy solo se implementa/prueba español; el campo existe para no rediseñar cuando se añada inglés. |
| Colores | `ReportConfig.accent_color_hex` (por defecto el de CargoOptimizer3D; sobrescribible con el color de marca del cliente) | Un único color de acento (cabeceras de tabla, títulos) — no una paleta completa; ver sección 13 para por qué se descarta un sistema de temas completo por ahora. |
| Pie de página | `ReportConfig.footer_text` (plantilla con marcadores `{company}`, `{date}`, `{page}`, `{pages}`) | Resuelto por `layout.py` en el *page callback*, nunca calculado en `sections.py`. |
| Cabecera | `ReportConfig.header_logo_position` (`"left"`/`"right"`/`"center"`) + `CompanyProfile.logo_path` | Misma función de `layout.py` que el pie; cabecera y pie comparten el mismo mecanismo de *callback*, no dos implementaciones. |
| Numeración | Automática, vía `layout.py` (`canvas.getPageNumber()` + un conteo total resuelto en una segunda pasada de ReportLab, patrón estándar de "Página X de Y") | No configurable en si existe o no en esta fase — siempre presente; si se pidiera desactivarla, sería un campo booleano nuevo en `ReportConfig`, cambio menor. |
| Marca de agua | `ReportConfig.watermark_text: str | None` | `None` = sin marca de agua (por defecto, salvo el informe de diagnóstico, sección 4); un texto diagonal semitransparente dibujado por `layout.py` en el mismo *callback* de página. |

## 6. Integración con el visor 3D

**Diseño únicamente — no se implementa nada de esta sección en 9.0 ni en 9.1 si 9.1 se acota a
generación sin captura.**

Restricción de partida: `Packing3DViewer` (`presentation/desktop/viewer/widget.py`) **no tiene hoy
ningún método de captura de imagen** — la fase 6.2 ("filtros, etiquetas, vistas, captura de imagen")
sigue pendiente (ver `docs/Roadmap.md`). `ADR-0010` ya anticipó este uso explícitamente: *"Modo
`off_screen=True` de primera clase, útil para pruebas y para una futura captura de imágenes en
servidor"* y `docs/ThreeDViewerDesign.md`, sección 18, ya reservó el contrato
`capture_image(path, *, resolution=None, transparent_background=False)` con la nota *"uso futuro:
incrustar la imagen capturada en un PDF (fase 8)"*. Este diseño solo formaliza esa intención ya
registrada.

Regla de capas no negociable: **`infrastructure/pdf` nunca importa PyVista, VTK ni
`presentation.desktop.viewer`** — igual que `infrastructure/excel` nunca importa PySide6. La captura
de imagen es responsabilidad exclusiva de `presentation/desktop`; `infrastructure/pdf` solo recibe el
resultado ya calculado.

Contrato propuesto para `ReportContent` (sección 2): un campo opcional
`viewer_screenshot_png: bytes | None`. `MainWindow` (o quien orqueste la generación del informe) lo
rellena así:

1. Si el visor está disponible (`Packing3DViewer.is_available()`) y hay una ventana abierta con el
   resultado ya mostrado: usar el método de captura que añada la fase 6.2
   (`capture_image`, ya diseñado en `docs/ThreeDViewerDesign.md`), leer los bytes del archivo temporal
   resultante y pasarlos a `ReportContent`.
2. Si el visor no está disponible (modo fallback, sin OpenGL) o el informe se genera sin ninguna
   ventana abierta (uso futuro por lotes o vía una hipotética `presentation/api`): `viewer_screenshot_png
   = None`, y `sections.py::build_executive_summary_section`/`build_client_section` simplemente omiten
   esa imagen — nunca fallan por su ausencia (mismo criterio de "modo limitado nunca bloquea" ya
   aplicado al catálogo SQLite en la fase 7.1).

Alternativa evaluada y **no** recomendada para la primera implementación: que
`infrastructure/pdf` reconstruya su propia escena reutilizando `SceneBuilder`/`SceneModel`
(`presentation/desktop/viewer/scene_builder.py`, que ya no depende de Qt ni de PyVista, solo de
`domain`) en un `pv.Plotter(off_screen=True)` propio, para poder generar informes sin ninguna ventana
abierta. Es técnicamente posible y no rompería la regla de capas si `scene_builder.py`/`models.py`
se movieran a un lugar accesible desde `infrastructure` (p. ej. un futuro paquete neutral) — pero eso
es una reestructuración de `presentation/desktop/viewer/`, no algo que esta fase de PDF deba forzar.
Se documenta aquí como la ruta a evaluar **si en el futuro** se necesita generar informes sin
interfaz gráfica abierta (por ejemplo, una fase 10 con `presentation/api`); hasta entonces, capturar
desde la ventana ya abierta es más simple y no exige mover código de `presentation` a un lugar nuevo.

## 7. Sistema de plantillas

`ReportTemplate` (`templates.py`) es el mecanismo único que expresa "qué informe generar":

```python
@dataclass(frozen=True, slots=True)
class ReportTemplate:
    key: str                                  # "executive_summary", "technical_full", ...
    display_name: str                         # "Resumen ejecutivo"
    sections: tuple[ReportSection, ...]       # orden exacto de secciones a incluir
    config_overrides: ReportConfigOverrides   # p. ej. marca de agua forzada, idioma por defecto
    is_builtin: bool = True
```

Los cinco informes oficiales de la sección 3 son cinco instancias constantes de esta clase — no
cinco clases Python distintas, no cinco funciones `generate_executive_summary`/
`generate_technical_report`/etc. `report_builder.py::generate_report` tiene una única firma:

```python
def generate_report(
    content: ReportContent,
    template: ReportTemplate,
    config: ReportConfig,
    path: Path,
) -> None: ...
```

Esto es exactamente el mismo movimiento de diseño que `advanced_export.py` (fase 8.1) ya aplicó a
la exportación de Excel: en vez de una función por variante, una única función parametrizada por una
estructura de datos que describe la variante. Mismo criterio, mismo beneficio: añadir un sexto tipo
de informe en el futuro no es escribir código nuevo, es declarar una sexta constante `ReportTemplate`.

## 8. Personalización futura

Pedido explícitamente por el encargo como diseño para fases posteriores (no implementar ahora):

- **Activar/desactivar secciones**: ya resuelto por la propia forma de `ReportTemplate.sections`
  (una tupla) — una UI futura de personalización solo necesita marcar/desmarcar casillas que
  añaden o quitan valores del enum `ReportSection` de esa tupla, sin ningún cambio en
  `report_builder.py`/`sections.py`.
- **Reordenar secciones**: mismo mecanismo — `sections.py::build_section(section, ...)` es una
  función de despacho por el valor del enum, así que el orden de la tupla es literalmente el orden de
  generación. Reordenar es reordenar la tupla.
- **Guardar plantillas propias**: se propone reutilizar el patrón ya construido y probado en la fase
  8.1 para `ImportMappingProfileRepository` (`infrastructure/database/repositories.py`): una tabla
  nueva `pdf_report_templates` en la **misma** base SQLite del catálogo (nunca una base de datos
  nueva), con `is_builtin=True` protegiendo los cinco oficiales de edición directa (solo
  duplicables), borrado lógico (`is_active`) y una columna JSON para `sections`/`config_overrides` —
  mismo criterio exacto de serialización que `column_mapping_json`. Esto es una decisión de diseño
  para cuando se implemente (fase posterior a 9.1), no un compromiso de código en esta fase: no se
  toca `infrastructure/database` en la fase 9.0 (instrucción explícita del encargo).

Ninguna de estas tres capacidades exige un diseño distinto al ya descrito en las secciones 2 y 7 —
es la razón por la que se optó por `ReportTemplate` como datos en vez de una jerarquía de clases: la
personalización futura es manipulación de datos, no herencia nueva.

## 9. Flujo de generación de extremo a extremo

Ilustrativo (no código real, `presentation/desktop` no se modifica en esta fase):

1. El usuario abre "Exportar informe PDF…" en `MainWindow`, con un `PackingResult` ya calculado
   (misma precondición que `_on_export_result_excel`, fase 8.0).
2. Un diálogo (fase 9.1, no diseñado en detalle aquí — mismo patrón de las cuatro diálogos de la
   fase 8.1) deja elegir el tipo de informe (una de las cinco `ReportTemplate` oficiales),
   rellenar `ClientInfo` si aplica, y confirmar/editar `CompanyProfile` (precargado desde donde se
   decida persistirlo, sección 8).
3. `MainWindow` construye `ReportContent` a partir de `self._last_result`, `self._current_project` y
   `self.product_table_panel.model.load_units()` (resolución de SKU, mismo patrón que
   `export_packing_result`), y captura `viewer_screenshot_png` si el visor está disponible (sección 6).
4. `MainWindow` llama a `generate_report(content, template, config, path)`. `infrastructure/pdf` no
   sabe nada de `MainWindow`, `QSettings`, SQLite ni PyVista — solo recibe datos ya resueltos.
5. Cualquier fallo de generación (`PdfError`) se muestra con `QMessageBox.critical`, igual que
   cualquier otro error de exportación ya establecido en la fase 8.0/8.1.

## 10. Dependencias y regla de capas

`infrastructure/pdf` depende únicamente de `domain` (para los tipos que recibe en `report_content.py`,
igual que `infrastructure/excel`) y de `reportlab` (dependencia de terceros, nueva, a añadir en la
fase 9.1 — **no en esta fase**). Nunca de `optimization`, `presentation`, `infrastructure/excel` ni
`infrastructure/database`. Se verificará con `import-linter` igual que el resto de subpaquetes de
`infrastructure` cuando exista código real que analizar; hoy no hay nada que verificar porque el
paquete no existe todavía.

## 11. Seguridad

Diseño equivalente al ya aplicado en `infrastructure/excel` (`docs/Excel.md`, sección 12):
- Ninguna ruta de archivo (informe de salida, logo de empresa/cliente) se construye a partir de texto
  de usuario sin pasar por `pathlib.Path`.
- La escritura del PDF final pasa por el mismo patrón de escritura atómica (archivo temporal en el
  mismo directorio + `os.replace`) que `save_workbook_atomic`/`ProjectFileRepository.save` — un corte
  a mitad de generación nunca debe dejar un `.pdf` corrupto en la ruta final.
- Ninguna plantilla admite HTML/Jinja2 evaluado dinámicamente desde texto de usuario (los
  marcadores de `footer_text`, sección 5, son sustitución literal de un conjunto cerrado de claves
  conocidas — `{company}`, `{date}`, `{page}`, `{pages}` — nunca `str.format(**kwargs_arbitrarios)`
  ni `eval`).

## 12. Pruebas (diseño para la fase 9.1)

No se escriben pruebas en esta fase (no hay código que probar). Se deja diseñado para cuando exista
implementación:
- `report_content.py`: construir `ReportContent` desde un `PackingResult` de ejemplo y verificar que
  cada campo se resuelve correctamente (incluido el caso `weight_utilization_percent is None`).
- `sections.py`: cada función de sección probada de forma aislada (¿genera el número correcto de
  filas de tabla? ¿el texto del motivo aparece para cada `UnpackedUnit`?), sin necesitar generar un
  PDF completo para cada prueba.
- `report_builder.py`: round-trip mínimo (¿el archivo generado existe, abre con `pypdf`/similar sin
  error, tiene el número de páginas esperado para un caso con muchas filas?) para los cinco
  `ReportTemplate` oficiales.
- `layout.py`: numeración correcta con 1 página y con muchas; marca de agua presente solo cuando se
  configura.

## 13. Decisiones descartadas

- **HTML/CSS renderizado a PDF (WeasyPrint u otro)** en vez de ReportLab programático: se descarta
  porque el proyecto ya declaró ReportLab como la tecnología prevista desde la fase 8
  (`CLAUDE.md`, stack tecnológico) y porque el control de layout pixel a pixel de tablas
  multi-página (cortes de tabla, repetición de cabecera de tabla entre páginas) es más directo con la
  API de `platypus` que depurando reglas CSS de paginación.
- **Una clase por tipo de informe** (`ExecutiveSummaryReport`, `TechnicalReport`, ...) en vez de
  `ReportTemplate` como datos: descartada por la misma razón que `PackingStrategy` es un `Protocol` y
  no una jerarquía de herencia (`CLAUDE.md`, invariantes de `optimization`) — los cinco informes no
  tienen comportamiento distinto, solo distinta selección/orden de las mismas secciones; una
  jerarquía de clases añadiría abstracción sin ganar nada sobre una tupla de datos.
- **Persistir `CompanyProfile`/`ClientInfo` dentro del `.cargo3d`**: descartado por el mismo criterio
  ya establecido en `docs/ProjectFiles.md` — los datos de empresa no son estado de un proyecto
  concreto (un usuario no tiene una empresa distinta por proyecto), y el cliente de un informe es un
  dato efímero de la generación, no algo que deba viajar dentro del archivo de proyecto.
- **Un sistema de temas de color completo** (paleta de 5+ colores configurables) en vez de un único
  `accent_color_hex`: descartado por ahora — ningún encargo real ha pedido más que "los colores de mi
  marca en el informe", y un único color de acento ya resuelve cabeceras de tabla y títulos; ampliar a
  una paleta completa es un cambio aditivo sencillo el día que se pida.
- **Reconstruir la escena 3D dentro de `infrastructure/pdf`** (evitando depender de que
  `presentation/desktop` ya tenga una ventana abierta): descartado para la primera implementación,
  documentado en la sección 6 como ruta futura si se necesita generación sin interfaz — no se cierra
  la puerta, pero tampoco se sobrearquitecturan capacidades que nadie ha pedido todavía.
- **Un motor de plantillas de texto tipo Jinja2** para `footer_text`/textos configurables: descartado
  por el riesgo de seguridad de evaluar plantillas con lógica arbitraria (sección 11) y porque un
  conjunto cerrado de marcadores (`{company}`, `{date}`, `{page}`, `{pages}`) cubre el 100% de lo
  pedido en el encargo sin ese riesgo.

## 14. Revisión crítica

**1. ¿Qué parte de este diseño es la más compleja, y se justifica?**
`report_content.py` como capa de traducción intermedia entre `domain` y `sections.py` es la pieza
menos "gratis" del diseño — sería más rápido, en el corto plazo, que `sections.py` recibiera
`PackingResult`/`LoadUnit` directamente. Se mantiene la capa intermedia de todas formas porque replica
un patrón ya validado tres veces en este proyecto (`SceneModel` en el visor 3D, los `*ImportResult`
de Excel, y el propio `ReportBuilder`-a-secas de Excel `build_packing_result_workbook`): aislar la
librería de renderizado (`reportlab`) de las entidades de dominio para que un cambio en cualquiera de
los dos lados no obligue a tocar el otro. El coste es un módulo más; el beneficio ya se ha visto
pagar en las fases 6 y 8.

**2. ¿Qué se podría simplificar sin perder nada real?**
La distinción entre `report_config.py` y `templates.py` podría fusionarse en un único módulo si el
número de campos de configuración se mantiene pequeño — se mantienen separados aquí porque
`ReportConfig` es "cómo se ve cualquier informe" (branding, idioma) y `ReportTemplate` es "qué lleva
este informe concreto" (secciones, overrides), y esa distinción importa para la sección 8
(personalización: el usuario cambia plantillas mucho más a menudo que su propio logo de empresa). Si
en la implementación real (9.1) el número de campos de cada uno resulta ser trivial, fusionarlos es
una simplificación legítima a decidir entonces, no ahora.

**3. ¿Qué decisión tiene más probabilidad de cambiar en el futuro?**
La estrategia de captura del visor 3D (sección 6): depender de una ventana ya abierta es la opción
más simple hoy, pero es la primera que se rompe si en el futuro se necesita generar informes sin
interfaz gráfica (un hipotético `presentation/api`, fase 10 si se llegara a implementar). Se acepta
el riesgo explícitamente porque nadie ha pedido generación headless todavía, y sobrediseñar para ese
caso ahora sería exactamente la sobrearquitectura que el encargo pide evitar.

**4. ¿Qué pasa si `reportlab` deja de mantenerse o cambia de licencia?**
El aislamiento de la sección 2 (`report_content.py`/`report_config.py` sin ningún import de
`reportlab`) significa que sustituir la biblioteca de renderizado exigiría reescribir
`sections.py`/`report_builder.py`/`layout.py`/`styles.py` (los módulos que sí la importan), pero
nunca tocar `domain`, `presentation`, ni la forma en que `MainWindow` invoca el sistema. Es el mismo
nivel de aislamiento que ya protege al proyecto frente a un cambio futuro de `openpyxl` en Excel o
de PyVista en el visor 3D — ninguna garantía es gratuita, pero el patrón ya está validado dos veces.

**5. ¿Es razonable que los cinco informes compartan el 100% del código de secciones?**
Es la apuesta central del diseño, y es revisable: si en la práctica el informe de cliente necesita
texto sustancialmente distinto (no solo ocultar columnas, sino redactar frases distintas) para cada
sección compartida, `build_executive_summary_section` tendría que ramificar internamente por
`ReportConfig.locale`/una bandera "modo cliente", lo cual empieza a oler a la jerarquía de clases que
se descartó en la sección 13. Se acepta el riesgo por ahora porque la matriz de la sección 4 muestra
que las diferencias reales entre informes son de **qué se incluye**, no de **cómo se redacta** cada
sección — si eso cambiara al implementar, sería una señal real para reconsiderar la decisión, no un
fallo de este diseño.

**6. ¿Qué debe entrar obligatoriamente en la fase 9.1 (implementación)?**
Los cinco tipos de informe con contenido real (sección 4), configuración de empresa/cliente/idioma
español/color de acento/cabecera/pie/numeración, marca de agua, y el flujo completo descrito en la
sección 9 **sin** captura del visor 3D si la fase 6.2 (captura de imagen) no está lista todavía —
`viewer_screenshot_png = None` es un estado válido y probado, no un bloqueante.

**7. ¿Qué debe aplazarse más allá de la 9.1?**
Plantillas guardadas por el usuario en SQLite (sección 8), inglés como segundo idioma real (el campo
existe, el diccionario de etiquetas en inglés no), captura de imagen sin ventana abierta (sección 6),
y cualquier editor visual de plantillas.
