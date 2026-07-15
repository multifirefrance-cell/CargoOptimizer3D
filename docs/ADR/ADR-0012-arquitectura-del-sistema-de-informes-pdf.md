# ADR-0012: Arquitectura del sistema de informes PDF

## Estado

Aceptada — 2026-07-15

## Contexto

La fase 9.0 diseña (sin implementar) el sistema de generación de
informes PDF profesionales de CargoOptimizer3D, descrito en detalle en
`docs/PdfReportDesign.md`. `CLAUDE.md` ya declaraba desde la fase 8 que
ReportLab sería la biblioteca prevista para PDF ("ReportLab para PDF
llega en una fase posterior"); esta ADR no reabre esa elección de
biblioteca, sino que fija las decisiones de arquitectura interna del
nuevo paquete `infrastructure/pdf/` — cinco tipos de informe distintos,
que comparten la mayor parte de su contenido, con integración opcional
de una captura del visor 3D que hoy no existe todavía (fase 6.2
pendiente).

Se evaluaron tres decisiones concretas con alternativas reales:

1. Cómo modelar cinco tipos de informe sin duplicar lógica de
   contenido entre ellos.
2. Cómo aislar `domain` de la biblioteca de renderizado (`reportlab`).
3. Cómo integrar la captura del visor 3D sin romper la regla de capas
   (`infrastructure` nunca depende de `presentation`).

## Decisión

**1. Un único `ReportTemplate` de datos, no una jerarquía de clases por informe.**
Los cinco informes oficiales (resumen ejecutivo, informe técnico completo, packing list
optimizado, informe interno de diagnóstico, informe para cliente) son cinco instancias constantes
de un mismo tipo `ReportTemplate` (`sections: tuple[ReportSection, ...]` + overrides de
configuración), nunca cinco subclases o cinco funciones `generate_*` distintas.
`report_builder.py::generate_report(content, template, config, path)` tiene una única firma para
los cinco. Añadir un sexto informe en el futuro es declarar una sexta constante, no escribir código
nuevo.

**2. `report_content.py`/`report_config.py` sin ningún import de `reportlab`.**
La traducción de `domain` (`PackingResult`, `CargoProject`, `LoadUnit`) a lo que hay que mostrar
(`ReportContent`) y la configuración de aspecto (`ReportConfig`, `CompanyProfile`, `ClientInfo`) son
dataclasses puros. Solo `sections.py`/`report_builder.py`/`layout.py`/`styles.py` importan
`reportlab`. `presentation/desktop` puede construir y validar esta configuración (un futuro
formulario "Datos de la empresa") sin que `reportlab` esté siquiera instalado en ese contexto de
pruebas.

**3. La captura del visor 3D se recibe ya resuelta (`bytes | None`), nunca se genera dentro de
`infrastructure/pdf`.**
`infrastructure/pdf` nunca importa PyVista, VTK ni `presentation.desktop.viewer` — el campo
`ReportContent.viewer_screenshot_png: bytes | None` lo rellena quien orquesta la generación
(`presentation/desktop`, ver `docs/PdfReportDesign.md`, sección 6), usando la captura de imagen que
añadirá la fase 6.2 al visor. `None` es un estado válido y no bloqueante (mismo criterio que el
modo limitado del catálogo SQLite, fase 7.1).

## Consecuencias

**Beneficios:**

- Ningún módulo del sistema de informes depende de tener los cinco informes "terminados" para
  empezar a funcionar: los cinco comparten el 100% del código de secciones (`sections.py`), así que
  el primero que se implemente ya deja los otros cuatro casi resueltos (solo una nueva constante
  `ReportTemplate`).
- `report_content.py`/`report_config.py` son comprobables sin `reportlab` instalado, igual que
  `CatalogImportPreview`/`ImportPlan` (fase 8.1) son comprobables sin `openpyxl` en la ruta de
  ejecución de esas pruebas concretas.
- La regla de capas (`infrastructure` nunca importa `presentation`) se mantiene intacta sin ningún
  caso especial: el visor 3D sigue siendo responsabilidad exclusiva de `presentation/desktop`.

**Costes / riesgos aceptados:**

- **Compartir secciones entre los cinco informes asume que las diferencias son de "qué se incluye",
  no de "cómo se redacta".** Documentado como el riesgo más probable de reconsiderar en
  `docs/PdfReportDesign.md`, sección 14, pregunta 5: si el informe de cliente necesitara redacción
  sustancialmente distinta (no solo ocultar columnas) en una sección compartida, esa sección tendría
  que ramificar internamente por configuración — un olor a la jerarquía de clases que esta ADR
  descarta. Se acepta el riesgo porque la matriz de contenido (`docs/PdfReportDesign.md`, sección 4)
  no muestra hoy esa necesidad.
- **Depender de una ventana del visor ya abierta para la captura de imagen** es más simple que
  reconstruir la escena dentro de `infrastructure/pdf`, pero es la primera pieza que se rompería si
  en el futuro se necesitara generación de informes sin interfaz gráfica abierta (un hipotético
  `presentation/api`). Se acepta explícitamente por ahora — nadie ha pedido generación headless
  todavía (`docs/PdfReportDesign.md`, sección 6 y sección 13).
- **`reportlab` no se ha instalado ni probado todavía** en este proyecto: la compatibilidad exacta
  con Python 3.12 y con el resto de dependencias se verificará al implementar (fase 9.1), no se da
  por hecha en esta fase de diseño — mismo criterio de honestidad que ADR-0010 aplicó a PyVista.
