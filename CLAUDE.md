# CLAUDE.md — Instrucciones permanentes para CargoOptimizer3D

Este archivo contiene las reglas que rigen el proyecto en todas las
sesiones futuras. No son sugerencias: son restricciones de arquitectura
y de producto que deben respetarse salvo decisión explícita en
contrario del arquitecto del proyecto.

## Qué es este software

CargoOptimizer3D es un producto **comercial**, no un prototipo. Se
diseña para mantenerse durante al menos diez años. Prioriza siempre
arquitectura sobre velocidad de entrega. No se acepta una solución
inferior solo por ser más rápida de escribir. Debe poder distribuirse
como Desktop, API, SDK embebido en un ERP, servicio o aplicación web
sin reescribir el motor.

## Vocabulario de dominio (obligatorio)

El sistema es universal, no está orientado a contenedores marítimos
específicamente.

- **Loading Space**: cualquier espacio de carga (contenedor marítimo,
  camión, furgón, van, semirremolque, bodega, plataforma, vagón,
  avión o espacio definido por el usuario). Nunca usar "contenedor"
  como concepto genérico en el código, la API o el dominio.
- **Load Unit**: cualquier unidad a cargar (caja, pallet, cilindro,
  tambor, bobina, tubo, maquinaria, carga irregular, grupo de cajas).
  Nunca usar "producto" como concepto genérico en el código, la API o
  el dominio.

Esta terminología se aplica a nombres de clases, módulos, tablas de
base de datos, endpoints de API y textos de interfaz. Justificación
completa en `docs/ADR/ADR-0002-vocabulario-loading-space-load-unit.md`.

## Arquitectura no negociable

Arquitectura en capas (Clean Architecture / Hexagonal), regla de
dependencia estricta — cada capa solo importa las que están por debajo:

```
presentation  →  infrastructure  →  application  →  optimization  →  rules  →  geometry  →  domain
  (externa)                                                                              (interna)
```

- **`domain`**: entidades y reglas de negocio puras (`LoadingSpace`,
  `LoadUnit`, invariantes). No depende de nada, ni del propio proyecto
  ni de bibliotecas externas de UI/persistencia/ofimática/visualización.
- **`geometry`**: cálculos espaciales deterministas (cajas ortoédricas,
  colisiones, soporte, límites, layouts). Depende solo de `domain`. Ver
  `docs/GeometryEngine.md` y ADR-0006.
- **`rules`**: motor de reglas de negocio (orientaciones permitidas,
  extintores, apilamiento, fragilidad, peso). Responde si una
  colocación es válida; no decide dónde colocar nada. Depende de
  `domain` siempre y de `geometry` solo donde una regla necesita
  información espacial. Ver `docs/RulesEngine.md` y ADR-0007.
- **`optimization`**: motor de empaquetado real (expansión de
  instancias, orden, generación y puntuación de candidatos,
  estrategia `greedy_extreme_point_v1`). Decide dónde colocar cada
  instancia; nunca reimplementa reglas ni geometría. Depende de
  `domain`, `geometry` y `rules`. Ver `docs/OptimizationEngine.md`,
  ADR-0008 y ADR-0009.
- **`application`**: casos de uso, orquestación, puertos (interfaces)
  hacia `infrastructure`. Depende de `domain`, `geometry`, `rules` y
  `optimization`.
- **`infrastructure`**: adaptadores concretos que implementan los
  puertos de `application`. Desde la fase 7.0 incluye
  `infrastructure/persistence/` (proyectos `.cargo3d`, JSON propio —
  ver `docs/ProjectFiles.md`); desde la fase 7.1 incluye
  `infrastructure/database/` (catálogo de productos, perfiles de
  Loading Space y, desde la fase 8.1, perfiles de mapeo de columnas de
  Excel; SQLAlchemy/SQLite — ver `docs/Database.md`); desde la fase 8.0
  incluye `infrastructure/excel/` (importación/exportación profesional
  de `.xlsx` con openpyxl — ver `docs/Excel.md`), ampliado en la fase
  8.1 con mapeo de columnas, vista previa, importación parcial,
  duplicados, informes y exportación avanzada, sin ningún formato
  nuevo — ver `docs/ExcelAutomation.md`. `infrastructure/pdf/`
  (informes PDF, ReportLab) se diseñó por completo en la fase 9.0 sin
  crear código todavía — ver `docs/PdfReportDesign.md` y ADR-0012; su
  implementación llega en la fase 9.1.
- **`presentation`**: mecanismos de entrega (`presentation/desktop`
  hoy con PySide6 y, dentro de él, `presentation/desktop/viewer/` con
  PyVista/PyVistaQt para el visor 3D — ver `docs/ThreeDViewer.md`;
  `presentation/api` o web en el futuro, como hermanos, sin tocar el
  código existente).

Esta regla se verifica automáticamente con `import-linter` (contrato
`layers` en `pyproject.toml`), no es solo documentación. Detalle
completo y justificación en `docs/Architecture.md` y
`docs/ADR/ADR-0001-arquitectura-en-capas.md`.

El núcleo (`domain` + `optimization`, y `application` cuando exista)
es un SDK independiente: ya puede usarse con
`from cargo_optimizer import PackingEngine, PackingRequest` sin
ninguna dependencia de UI instalada (ADR-0003).

## Stack tecnológico

- Python 3.12+, tipado obligatorio (type hints en todo el código
  nuevo).
- PySide6 para la interfaz de escritorio.
- PyVista + PyVistaQt (sobre VTK) para el visor 3D
  (`presentation/desktop/viewer/`, implementado en la fase 6.1 — ver
  `docs/ThreeDViewer.md`).
- JSON propio (`json` de la biblioteca estándar) para persistencia de
  proyectos (`.cargo3d`, fase 7.0, implementada — ver
  `docs/ProjectFiles.md`). SQLite + SQLAlchemy 2.x para el catálogo de
  productos, perfiles de Loading Space e historial (fase 7.1,
  implementada — ver `docs/Database.md`); base de datos ubicada en
  `%LOCALAPPDATA%/CargoOptimizer3D/`, nunca dentro del repositorio ni
  versionada.
- openpyxl para importación/exportación de Excel (`.xlsx`, fase 8.0,
  implementada — ver `docs/Excel.md`; automatización del flujo —mapeo
  de columnas, perfiles, vista previa, duplicados, drag&drop,
  importación masiva, informes, exportación avanzada— en la fase 8.1,
  implementada — ver `docs/ExcelAutomation.md`); nunca `pandas`,
  `xlrd` ni CSV como sustituto. ReportLab para informes PDF: diseño
  completo en la fase 9.0 (`docs/PdfReportDesign.md`, ADR-0012),
  **todavía sin instalar ni implementar** — la dependencia se añade
  recién en la fase 9.1.
- Ruff para lint (incluye orden de imports). Black para formateo. No
  usar el formateador de Ruff para evitar conflictos con Black.
- Mypy en modo estricto (`strict = true`).
- import-linter para verificar automáticamente la regla de capas.
- Pytest para pruebas.

## Estructura del repositorio

```
src/cargo_optimizer/
├── domain/          # Entidades y reglas de negocio puras. Sin dependencias externas.
├── geometry/        # Cálculos espaciales deterministas. Depende solo de domain.
├── rules/           # Motor de reglas de negocio. Depende de domain y, si hace falta, de geometry.
├── optimization/    # Motor de empaquetado real. Depende de domain, geometry y rules.
├── application/     # Casos de uso, orquestación, puertos hacia infraestructura.
├── infrastructure/  # Adaptadores concretos: persistence/ (proyectos .cargo3d, JSON, fase 7.0),
│                    #   database/ (catálogo SQLite/SQLAlchemy, fase 7.1 + perfiles de mapeo, fase 8.1),
│                    #   excel/ (import/export .xlsx, fase 8.0 + automatización, fase 8.1),
│                    #   pdf/ (diseñado en fase 9.0, docs/PdfReportDesign.md; sin implementar).
└── presentation/
    └── desktop/     # Aplicación de escritorio PySide6. Incluye viewer/ (visor 3D, PyVista/PyVistaQt).
tests/               # Pruebas, en espejo de la estructura de src/, + tests/integration/
docs/                # Architecture.md, Roadmap.md, GeometryEngine.md, RulesEngine.md,
                     # OptimizationEngine.md (implementación real),
                     # OptimizationEngineDesign.md, GreedyLayerStrategyDesign.md (diseño), ADR/
examples/            # Proyectos de ejemplo de uso del SDK
userdata/            # Datos generados por el usuario en tiempo de ejecución. Nunca se versiona su contenido.
```

## Comandos de referencia

```powershell
.\.venv\Scripts\python.exe -m cargo_optimizer   # ejecutar la app
.\.venv\Scripts\python.exe -m ruff check .      # lint
.\.venv\Scripts\python.exe -m black .           # formateo
.\.venv\Scripts\python.exe -m mypy src          # tipado
.\.venv\Scripts\lint-imports.exe                # regla de capas (import-linter)
.\.venv\Scripts\python.exe -m pytest            # tests
```

## Fases del proyecto

0. Diseño completo — 1. Arquitectura — 2.1. Modelo de dominio puro —
   2.2. Motor geométrico — 3. Motor de restricciones — 4.0. Diseño del
   motor de optimización — 4.1. Primer optimizador funcional — 4.2.
   Optimización de rendimiento del motor de packing — 5.0. Base de la
   interfaz de escritorio — 5.1. Conectar el motor con la interfaz —
   6.0. Diseño del visor 3D — 6.1. Visor 3D: implementación mínima —
   6.2. Visor 3D: filtros/etiquetas/vistas/captura — 6.3. Visor 3D:
   animación y escala — 7.0. Persistencia de proyectos (.cargo3d,
   JSON) — 7.1. Catálogo de productos y perfiles reutilizables
   (SQLite/SQLAlchemy) — 8.0. Importación y exportación profesional de
   Excel — 8.1. Automatización del flujo Excel (mapeo de columnas,
   perfiles, vista previa, importación parcial, duplicados, drag&drop,
   importación masiva, informes, exportación avanzada) — 9.0. Diseño
   del sistema profesional de informes PDF — 9.1. Informes PDF:
   implementación — 10. Integración ERP — 11. Versión comercial.

La fase 2 original ("Motor geométrico") se dividió en 2.1 (modelo de
dominio puro) y 2.2 (motor geométrico) para poder completar el modelo
de dominio sin implementar todavía colisiones ni packing. Ver
`docs/Roadmap.md`, sección "Nota sobre la numeración de la fase 2". La
fase 4 se dividió igual, en 4.0 (diseño puro) y 4.1 (implementación),
por el mismo motivo: no crear `optimization/` antes de haber diseñado
qué contendrá. La fase 5 se renumeró de "5 = Visualización 3D, 6 =
Interfaz" a "5.0/5.1 = Interfaz, 6 = Visualización 3D" al construir la
interfaz antes que VTK. La fase 6 corrige además el paquete: el visor
no pertenece a `infrastructure` (como decía la fila original) sino a
`presentation/desktop/viewer/`, y se subdivide en 6.0 (diseño) / 6.1
(mínimo) / 6.2 (enriquecimiento) / 6.3 (escala y animación) — ver
`docs/Roadmap.md`, secciones "Nota sobre la numeración de las fases 5 y
6" y "Nota sobre la numeración y el paquete de la fase 6". La fase 8
se subdivide igual: 8.0 (Excel básico) y lo que originalmente era 8.1
(reportes PDF) pasó primero a 8.2; un segundo encargo real sobre el
módulo Excel ya en uso ocupó el hueco 8.1 con la automatización del
flujo (mapeo de columnas, perfiles, vista previa, importación parcial,
duplicados, drag&drop, importación masiva, informes, exportación
avanzada). Un tercer encargo, ya con 8.1 completada, renombró y
subdividió lo que era 8.2 como **fase 9**: **9.0** (diseño puro de los
informes PDF, esta entrega) y **9.1** (implementación, pendiente);
"Integración ERP" pasó de 9 a **10**, y "Versión comercial" de 10 a
**11** — ver `docs/Roadmap.md`, secciones "Nota sobre la numeración de
la fase 8" y "Nota sobre la numeración de la fase 9".

Estado actual: **diseño completo del sistema de informes PDF** (fin de
fase 9.0). `docs/PdfReportDesign.md` fija la arquitectura de
`infrastructure/pdf/` (ocho módulos: `exceptions.py`, `styles.py`,
`layout.py`, `report_config.py`, `report_content.py`, `sections.py`,
`templates.py`, `report_builder.py`, ninguno implementado todavía),
los cinco tipos de informe oficiales (resumen ejecutivo, informe
técnico completo, packing list optimizado, informe interno de
diagnóstico, informe para cliente) con su contenido exacto, la
configuración (empresa, cliente, idioma, colores, cabecera/pie,
numeración, marca de agua), el sistema de plantillas
(`ReportTemplate` como datos, nunca una jerarquía de clases por
informe — ADR-0012) y la integración diseñada — no implementada — con
el visor 3D (`ReportContent.viewer_screenshot_png: bytes | None`,
inyectado desde `presentation/desktop`, nunca calculado dentro de
`infrastructure/pdf`). **Esta fase no creó ningún código funcional de
PDF ni añadió `reportlab` como dependencia** — es exclusivamente de
documentación, tal como exigía el encargo.
`domain`/`geometry`/`rules`/`optimization`/`presentation`/
`infrastructure/database`/`infrastructure/excel` siguen intactos.

El visor 3D (fase 6.1) sigue disponible y sin cambios en esta fase —
ver `docs/ThreeDViewer.md` para su implementación completa
(arquitectura, selección, cámara, temas, fallback, el hallazgo del
segmentation fault de VTK bajo `offscreen`, etc.). La interfaz ejecuta
el motor real de principio a fin desde la fase 5.1: construye una
`PackingRequest` desde el formulario de Loading Space y la tabla de
productos, la ejecuta en `OptimizationWorker` (`QThread` dedicado),
vuelca el `PackingResult` en cuatro pestañas del panel inferior y en el
visor 3D, sin bloquear nunca el hilo de la interfaz. No implementar
todavía filtros/etiquetas/modos de color/vistas predefinidas/captura de
imagen del visor (fase 6.2 — un prerrequisito útil, no bloqueante, para
que los informes PDF de 9.1 incluyan la captura del visor),
animación/capas/cortes/escala del visor (fase 6.3), ningún código real
de `infrastructure/pdf` (fase 9.1), integración ERP (fase 10),
Undo/Redo, ni volver a tocar `domain`/`geometry`/`rules`/`optimization`
salvo bug objetivo y demostrable, hasta que se indique explícitamente.
Ver `docs/Roadmap.md` para el detalle fase a fase.

## Invariantes del modelo de dominio (no romper sin ADR)

Ver `docs/DomainModel.md` para el detalle completo. Resumen que
cualquier sesión futura debe respetar al tocar `src/cargo_optimizer/domain/`:

- Todas las entidades y value objects son
  `@dataclass(frozen=True, slots=True)` (ver ADR-0005). No añadir
  setters ni convertir ninguna a mutable sin un ADR que lo justifique.
- Los enums de dominio heredan de `enum.StrEnum`; sus valores string
  son un contrato estable de persistencia/API futura — no renombrarlos
  sin una migración documentada.
- Sistema de coordenadas fijo: X = largo, Y = ancho, Z = altura; origen
  en el suelo, esquina trasera izquierda. Todas las dimensiones > 0;
  todos los pesos >= 0; ninguna coordenada ni dimensión puede ser NaN
  o infinita.
- `LoadUnit.quantity` (paquetes solicitados), `units_per_package`
  (unidades por paquete) y `total_requested_units` (su producto) son
  conceptos distintos: no colapsarlos en un único campo.
- `LoadUnit.weight_kg` (peso bruto del paquete) y
  `extinguisher_nominal_kg` (carga nominal del agente extintor) son
  conceptos distintos, no intercambiables.
- Un `LoadUnit` con `is_extinguisher=False` siempre tiene
  `extinguisher_agent = not_applicable` y `extinguisher_nominal_kg =
  None`; con `is_extinguisher=True`, lo contrario. Esta regla está
  validada en `LoadUnit.__post_init__`, no debe relajarse.
- Ni `Orientation` ni `Placement` implementan detección de colisiones:
  esa lógica vive en `cargo_optimizer.geometry`, nunca en el modelo de
  dominio.
- La regla de horizontalidad obligatoria de extintores (no apilar de
  canto) es del motor de restricciones (fase 3), no del dominio ni de
  `geometry`. El dominio solo deja los campos necesarios preparados.

## Invariantes del motor geométrico (no romper sin ADR)

Ver `docs/GeometryEngine.md` para el detalle completo.

- `geometry` depende únicamente de `domain`; nunca de `application`,
  `infrastructure`, `presentation` ni de ninguna biblioteca externa.
  Verificado por `import-linter`.
- Toda comparación de punto flotante usa `GEOMETRY_EPSILON_CM`
  (`geometry/constants.py`, 1e-9 cm). No introducir tolerancias
  ad-hoc en otros módulos.
- `overlaps` (volumen positivo), `touches` (contacto sin volumen) e
  `intersects` (cualquiera de los dos) son relaciones distintas — ver
  ADR-0006. `boxes_overlap`/la detección de colisiones se basa en
  `overlaps`: tocarse nunca es una colisión.
- El área de soporte se calcula como unión de rectángulos
  (`geometry/rectangles.py`), nunca como suma ingenua: sumar áreas
  solapadas de cajas inferiores produciría un `support_ratio` > 1.0
  incorrecto.
- `find_overlapping_placements` y el resto de funciones de
  `geometry` son deterministas: misma entrada, misma salida, sin
  aleatoriedad ni dependencia de orden de iteración de `set`/`dict`
  no controlado.
- `geometry` no verifica peso máximo, reglas de extintores,
  fragilidad, orientación permitida ni orden de descarga: eso es del
  motor de restricciones (fase 3).

## Invariantes del motor de reglas (no romper sin ADR)

Ver `docs/RulesEngine.md` para el detalle completo.

- `rules` depende siempre de `domain`; de `geometry` solo donde una
  regla necesita información espacial. Nunca de `application`,
  `infrastructure`, `presentation` ni de ninguna biblioteca externa.
  Verificado por `import-linter`.
- **Extintores individuales >= 3 kg nominales**: horizontales, con la
  dimensión original `length_cm` paralela al eje X; máximo efectivo de
  apilamiento siempre 1. **Extintores de 1, 2 y 3 kg en cajas
  grupales sí pueden colocarse verticalmente** y apilarse hasta
  `max_stack_count`. Estas dos reglas son obligatorias y no deben
  relajarse ni fusionarse. Ver ADR-0007, Decisión 2.
- La regla de extintores usa siempre `extinguisher_nominal_kg`, nunca
  `weight_kg` (peso bruto del empaque).
- Las capacidades recomendadas de extintores grupales (10/8/6 por
  1/2/3 kg) son advertencias (`RuleSeverity.WARNING`), nunca motivo de
  rechazo.
- `RuleEvaluation.is_allowed` es `False` si y solo si hay al menos una
  violación `severity=error`; se construye con `.allowed()`,
  `.rejected()` o `.combine()`, nunca directamente.
- `evaluate_candidate_placement` no se detiene en la primera
  violación, salvo que haya colisión: en ese caso se omiten soporte,
  apilamiento, fragilidad y peso soportado (derivados de un volumen en
  disputa), pero límites, orientación, configuración de extintor y
  peso del espacio se evalúan siempre. Ver ADR-0007, Decisión 3.
- Ninguna función de `rules` modifica entidades de dominio ni tiene
  efectos secundarios: siempre devuelve un `RuleEvaluation` explícito.

## Invariantes del motor de optimización (no romper sin ADR)

Ver `docs/OptimizationEngine.md` para el detalle completo de la
implementación real (`docs/OptimizationEngineDesign.md` y
`docs/GreedyLayerStrategyDesign.md` son el diseño original de fase 4.0,
conservado como historial).

- `optimization` depende de `domain`, `geometry` y `rules`; nunca de
  `application`, `infrastructure`, `presentation` ni de bibliotecas
  externas. Verificado por `import-linter`.
- `PackingStrategy` es un `Protocol`, no una `ABC`. No introducir una
  jerarquía de herencia de estrategias sin una razón nueva y
  justificada.
- La primera estrategia es **extreme-point greedy**
  (`greedy_extreme_point_v1`, clase `GreedyExtremePointStrategy`), no
  *layering* estricto. No existe ningún `LayerManager` como componente
  global; no introducir uno sin justificación nueva.
- El *score* de candidatos es una tupla comparada lexicográficamente
  (`z, x, y, -support_ratio, incremento de bounding volume, espacio
  residual aproximado, orden de orientación, generation_index`), nunca
  una suma ponderada.
- Restricciones duras (de `rules`) y objetivos de optimización nunca
  se mezclan en un único sistema de puntuación: un candidato inválido
  (`RuleEvaluation.is_allowed = False`) ni siquiera compite por score.
- El motor es determinista: mismo `PackingRequest` → mismo
  `PackingResult` (salvo `execution_time_seconds`, un reloj de pared).
  Nunca iterar sobre un `set` cuyo orden importe; siempre listas/tuplas
  explícitamente ordenadas.
- Cajas que no caben nunca se expresan como excepción: se registran
  como `UnpackedUnit` con un `UnpackedReason` estable. Solo un fallo
  interno del propio motor (la validación final del layout detecta una
  inconsistencia) es una excepción real (`OptimizationInternalError`).
- La cancelación usa `threading.Event` (`CancellationToken`); el
  paquete `optimization` no importa nunca PySide6, ni siquiera para
  cancelación o progreso.
- Una excepción del `progress_callback` del usuario se convierte en
  advertencia (`PackingResult.warnings`) y la ejecución continúa;
  nunca se propaga ni corrompe el empaquetado.
- `PackingState.accepted_boxes` y `PackingState.bounding_dimensions`
  (fase 4.2) son cachés incrementales, actualizadas únicamente dentro
  de `accept_placement`: no reintroducir un recálculo desde cero de
  bounding box por candidato (fue el cuello de botella nº 1 medido por
  perfilado real antes de la fase 4.2, ver `docs/PerformanceBaseline.md`).
- `optimization/pruning.py` solo poda un punto candidato cuando es
  geométricamente **cierto** que ninguna orientación podrá colocarse
  ahí (fuera de límites, o estrictamente interior a una caja
  existente); nunca por heurística de "punto dominado". Un punto
  podado siempre contribuye su código de violación garantizado
  (`OUT_OF_BOUNDS`/`COLLISION`) al conjunto agregado de violaciones de
  la instancia, para no alterar `_classify_unpacked_reason`. No relajar
  esta garantía sin releer la prueba de corrección en el docstring del
  propio módulo.
- No filtrar `existing_placements` por proximidad espacial antes de
  pasarlo a `PlacementRuleContext`: se evaluó explícitamente en la fase
  4.2 y se descartó porque `stacking_rules.evaluate_supported_weight`
  necesita conocer todo lo que descansa, directa o transitivamente,
  sobre cada soporte en cualquier parte del layout, no solo lo cercano
  al candidato.
- **Rendimiento real sigue siendo O(n³)-ish tras la fase 4.2** (~80 s
  para 100 instancias con el escenario mixto de referencia, ~1.3x más
  rápido que antes de esa fase, no el 5x que era el objetivo
  obligatorio). No es un bug de `optimization`: el perfilado real
  (`docs/OptimizerPerformance.md`) muestra que el coste restante vive
  dentro de `RulesEngine.evaluate_placement` (soporte, apilamiento,
  peso soportado, colisión) — reducirlo de raíz exigiría una
  estructura de datos espacial dentro de `rules`/`geometry`, fuera del
  alcance de la fase 4.2. No prometer rendimiento distinto al
  documentado en `docs/OptimizerPerformance.md` sin haber implementado
  esa estructura, con ADR explícito.

## Invariantes de `presentation/desktop` (no romper sin ADR)

Ver `docs/Architecture.md`, sección `presentation`, para el detalle
completo de la estructura de `presentation/desktop/` construida en las
fases 5.0 y 5.1.

- `PackingEngine.optimize(...)` nunca se ejecuta en el hilo de la
  interfaz: solo `OptimizationWorker` (`workers/optimization_worker.py`,
  un `QThread`) lo invoca. No añadir una llamada directa a
  `PackingEngine`/`RulesEngine`/ninguna función de `optimization` desde
  `main_window.py` ni ningún panel — pasaría a bloquear la GUI durante
  toda la ejecución (segundos a minutos, ver
  `docs/OptimizerPerformance.md`).
- El `progress_callback` que recibe `PackingEngine.optimize(...)` (la
  función conectada a `OptimizationWorker.progress.emit`) se ejecuta
  **dentro del hilo del worker**: no debe tocar ningún widget
  directamente, solo emitir la señal `Signal(object)` — Qt entrega el
  objeto al hilo de la GUI mediante una conexión en cola automática
  porque emisor y receptor están en hilos distintos.
- La limpieza tras una ejecución (rehabilitar controles, ocultar la
  barra de progreso, liberar la referencia al worker) pasa siempre por
  `MainWindow._on_worker_thread_finished`, conectado a la señal
  `QThread.finished` nativa — nunca duplicar esa lógica en los
  manejadores de éxito/cancelación/error, para que solo haya un punto
  que decide "ya se puede volver a interactuar con la interfaz".
- La cancelación es cooperativa y asíncrona
  (`OptimizationWorker.cancellation_token.cancel()`): nunca se llama a
  `QThread.wait()` desde el hilo de la GUI para esperar una
  cancelación de usuario (bloquearía la interfaz, justo lo que se
  quería evitar). La única excepción deliberada es `closeEvent`, donde
  bloquear brevemente al cerrar la ventana sí es aceptable.
- Todos los errores (validación de la solicitud, fallo del motor,
  excepción inesperada del hilo del worker) se muestran con
  `QMessageBox` (`MainWindow._show_warning`/`_show_error`); nunca solo
  por consola ni silenciados. `OptimizationWorker.run()` captura
  cualquier excepción de `engine.optimize(...)` y la reenvía por la
  señal `optimization_failed`, precisamente para que nunca se pierda
  en el hilo secundario.
- Toda acción de menú o toolbar sin implementación real muestra
  "[acción]: disponible en una próxima versión." en la barra de
  estado (`MainWindow._stub`); nunca queda una acción sin `slot`
  conectado.
- `ProductTableModel` es un `QAbstractTableModel` sobre `LoadUnit`
  reales (frozen), no `QTableWidget` ni una copia paralela del
  esquema de dominio. Una edición reconstruye la instancia con
  `dataclasses.replace` y descarta el cambio (`setData` devuelve
  `False`) si el dominio la rechaza (`DomainValidationError`) — nunca
  se deja el modelo en un estado inconsistente ni se relaja la
  validación de dominio para permitir la edición.
- `LoadingSpaceFormPanel`: los campos del formulario permanecen
  deshabilitados y muestran el valor del perfil elegido mientras el
  perfil no sea "Personalizado"; solo "Personalizado" desbloquea
  edición libre. No cambiar este bloqueo a una edición siempre libre
  sin decisión explícita — es intencional, para que un perfil
  estándar nunca quede editado por accidente.
- Persistencia de estado **de la aplicación** (geometría/estado de la
  ventana, último directorio, último perfil de espacio, tema, lista de
  recientes) exclusivamente vía `QSettings`
  (`presentation/desktop/settings.py::AppSettings`) — nunca dentro de
  un archivo `.cargo3d`. Persistencia de estado **de un proyecto**
  (espacio, productos, resultado, y una fotografía de tema/splitters/
  docks visibles en el momento de guardar) exclusivamente en el
  archivo `.cargo3d` vía `ProjectFileRepository`
  (`infrastructure/persistence/`, fase 7.0) — nunca en `QSettings`. Ver
  `docs/ProjectFiles.md`, sección 4, para el desacoplo exacto entre
  ambos (`presentation_state` es un `dict` opaco para
  `infrastructure`, construido e interpretado solo por `MainWindow`).
- Los recursos (`resources/icons/*.svg`) viven dentro de
  `presentation/desktop/`, cargados por ruta de archivo directa
  (`icons.py::icon`) — no hay pipeline `.qrc`/`pyside6-rcc` todavía;
  no introducirlo sin necesidad real (más iconos, i18n de recursos).
- Las pruebas de `tests/presentation/desktop/` fijan
  `QT_QPA_PLATFORM=offscreen` antes de crear el primer `QApplication`
  (`conftest.py`), para no depender de un entorno gráfico ni abrir
  ventanas reales durante la suite. Solo puede existir un
  `QApplication` por proceso: el fixture `qapp` es de ámbito de
  sesión, nunca crear uno nuevo por prueba.

## Invariantes del visor 3D (`presentation/desktop/viewer/`, implementado en la fase 6.1, no romper sin ADR)

Implementación real documentada en `docs/ThreeDViewer.md`; diseño
original en `docs/ThreeDViewerDesign.md`; plan de fases en
`docs/ThreeDViewerImplementationPlan.md`; decisiones formales en
ADR-0010 (tecnología) y ADR-0011 (desacoplo y fallback).

- `viewer/` nunca importa `cargo_optimizer.optimization`: recibe
  siempre un `PackingResult` ya calculado
  (`Packing3DViewer.display_result(result, load_units_by_id)`), nunca
  ejecuta `PackingEngine`, `PackingRequest` ni `RulesEngine`. No lo
  impone hoy `import-linter` de forma automática — es disciplina de
  diseño verificable en revisión de código, igual que la separación
  entre `optimization` y `rules` ya documentada más arriba.
- `load_units_by_id: Mapping[UUID, LoadUnit]` se entrega junto al
  `PackingResult` para resolver SKU/nombre/peso/color de cada
  `Placement` — mismo patrón ya usado por `UnpackedUnitTableModel`
  desde la fase 5.1. No ampliar `PackingResult`/`Placement` con datos
  de `LoadUnit` para evitar este mapping (tocaría dominio sin
  necesidad real); no crear un DTO visual paralelo a `LoadUnit`
  mientras solo replicaría sus mismos campos.
- La geometría de la escena **nunca permuta ejes**: un punto
  `(x_cm, y_cm, z_cm)` del dominio se dibuja como `(x, y, z)` en
  PyVista, sin reordenar componentes. "Z arriba" se consigue con el
  parámetro de cámara `view_up = (0, 0, 1)`, nunca reordenando datos.
- El color de una caja viene de `LoadUnit.color_hex`; el color de
  repuesto (`ColorRegistry`, cuando el `LoadUnit` es desconocido) debe
  ser determinista **entre ejecuciones del programa**, no solo dentro
  de una — nunca usar `hash()` de Python sobre cadenas para esto
  (aleatorizado por proceso desde Python 3.3); usar un hash estable
  (`zlib.crc32`/`hashlib.md5`) sobre una paleta curada de alto
  contraste. Nunca `random` sin semilla.
- Seleccionar una caja cambia su contorno/resalte, nunca su color de
  relleno — cambiar el relleno pierde la asociación visual "este color
  = este SKU" justo cuando más se necesita.
- `Packing3DViewer` debe poder fallar al inicializar (PyVista no
  instalado, `QtInteractor` no arranca, sin OpenGL) sin tirar la
  aplicación: `is_available()` refleja el estado, y todos los métodos
  públicos se vuelven no-op seguros en modo fallback. `MainWindow`
  nunca comprueba `is_available()` antes de llamar a
  `display_result`/`clear_scene`/etc. — la responsabilidad es
  enteramente del widget.
- `set_selected_placement(...)`, cuando se llama desde fuera del
  widget (p. ej. desde una tabla), actualiza el estado visual sin
  volver a emitir la señal `placement_selected` — esa señal representa
  únicamente "el usuario seleccionó algo haciendo clic en el visor",
  para evitar un ciclo de señales con quien la escucha.
- Estrategia de renderizado (6.1): un actor por caja, no malla
  combinada ni glyphs — decisión revisable en 6.3 si el rendimiento del
  optimizador a gran escala lo justifica (ver
  `docs/OptimizerPerformance.md`, y el rendimiento medido en
  `docs/ThreeDViewer.md`, sección 12), pero no antes: el modelo de
  escena (`SceneModel`/`PlacementVisualModel`) ya está diseñado para no
  depender de esta estrategia concreta.
- `Packing3DViewer._try_create_interactor` comprueba
  `QApplication.platformName() == "offscreen"` **antes** de importar o
  construir `pyvistaqt.QtInteractor`, nunca dentro de un
  `try/except` como única defensa: construir un `QtInteractor` bajo la
  plataforma `offscreen` provoca un segmentation fault nativo de VTK en
  Windows, no una excepción Python capturable — ver
  `docs/ThreeDViewer.md`, sección 10. No revertir esta comprobación
  proactiva a un `try/except` reactivo sin releer ese hallazgo.

## Invariantes de persistencia de proyectos (`infrastructure/persistence/`, implementado en la fase 7.0, no romper sin ADR)

Formato completo documentado en `docs/ProjectFiles.md`.

- `infrastructure/persistence` depende únicamente de `domain`; nunca
  de `presentation`, ni de PySide6/Qt. `presentation_state` es un
  `Mapping[str, Any]` opaco que `ProjectFileRepository` serializa y
  deserializa sin interpretar — construirlo/leerlo es responsabilidad
  exclusiva de `MainWindow`. No introducir tipos de Qt (`QByteArray`,
  `QColor`, etc.) dentro de `serialization.py`/
  `project_file_repository.py`.
- Serialización explícita campo a campo (`serialization.py`), nunca
  `pickle`, `jsonpickle`, ni volcado de `__dict__`. Añadir un campo
  nuevo a una entidad de `domain` exige actualizar a mano su función
  `_to_dict`/`_from_dict` correspondiente — no hay generación
  automática que lo haga por ti, y olvidarlo no falla en tiempo de
  tipado (los diccionarios son `dict[str, Any]`), solo en tests o en
  producción.
- Escritura siempre atómica: archivo temporal en el mismo directorio
  del destino + `os.replace`. Nunca escribir directamente sobre la
  ruta final con `path.write_text(...)` — un corte a mitad de la
  escritura dejaría un `.cargo3d` corrupto en vez de, en el peor caso,
  un `.tmp` huérfano.
- `save()` hace un backup de un solo nivel (`<archivo>.cargo3d.bak`)
  antes de sobrescribir un archivo existente — no un historial de
  versiones. No confundir esto con control de versiones; si se
  necesita en el futuro, es una decisión nueva con su propio ADR.
- `schema_version` (versión del formato del archivo) es un campo
  completamente distinto de `application_version` (qué build de
  CargoOptimizer3D lo escribió). La compatibilidad se decide siempre
  por `schema_version`, nunca comparando `application_version`.
  `_ensure_supported_schema_version` en `project_file_repository.py`
  es el único punto de extensión para migraciones futuras — hoy solo
  acepta `"1.0"`; añadir una versión nueva exige escribir la función de
  migración real, no solo ampliar el conjunto de versiones aceptadas.
- `CargoProject.name` se deriva del nombre del archivo (`path.stem`) al
  guardar — no existe todavía un campo de "nombre de proyecto"
  editable independiente del nombre de archivo. No inventar ese
  concepto sin necesidad real confirmada (ver "Mejoras futuras" en
  `docs/ProjectFiles.md`).
- `MainWindow` nunca vuelve a ejecutar `PackingEngine` automáticamente
  al detectar que el proyecto cambió después de calcular un resultado:
  solo marca el resultado como desactualizado
  (`_result_stale`/`ResultsPanel.set_stale`) e informa con el mensaje
  exacto "El resultado anterior fue invalidado porque el proyecto
  cambió." — recalcular automáticamente sería sorprendente (el usuario
  no pidió optimizar) y potencialmente costoso (ver
  `docs/OptimizerPerformance.md`).
- Las pruebas de `presentation/desktop` tienen una red de seguridad
  `autouse` en `conftest.py`
  (`_no_blocking_question_dialog`) que sustituye `QMessageBox.question`
  por una respuesta "Descartar" por defecto — sin ella, cualquier
  prueba que deje la ventana con cambios sin guardar y llame a
  `window.close()` se cuelga esperando un diálogo real bajo la
  plataforma `offscreen`. No eliminar esa fixture; si una prueba
  necesita otra respuesta (Guardar/Cancelar), debe sobrescribirla
  localmente con su propio `monkeypatch`, nunca depender de que el
  diálogo real responda.

## Invariantes del catálogo SQLite (`infrastructure/database/`, implementado en la fase 7.1, no romper sin ADR)

Detalle completo en `docs/Database.md` (esquema, versionado,
repositorios, `CatalogService`, modo limitado, seguridad).

- `infrastructure/database` depende de `domain` y de SQLAlchemy; nunca
  de `presentation`, ni de PySide6/Qt. Los modelos ORM
  (`orm_models.py`) son un mapeo puro a tablas, sin métodos de UI ni
  lógica de negocio; nunca se exponen fuera de `infrastructure` — todo
  cruce hacia/desde `domain` pasa por una conversión explícita
  (`_orm_to_load_unit`, `_orm_to_loading_space`, etc.), nunca por
  `__dict__` ni mapeo automático.
- El catálogo SQLite y los archivos `.cargo3d` son dos mecanismos de
  persistencia con propósitos distintos y **sin dependencia entre
  sí**: SQLite guarda datos reutilizables entre proyectos (productos,
  perfiles, historial); `.cargo3d` es la fotografía completa y portable
  de un proyecto. Ningún `.cargo3d` puede depender de que una fila del
  catálogo siga existiendo. Copiar un producto o perfil del catálogo a
  un proyecto (`CatalogService.copy_to_project`/
  `copy_profile_to_project`) siempre genera un `LoadUnit`/
  `LoadingSpace` con un `UUID` nuevo — una copia completa e
  independiente, nunca una referencia — ver `docs/ProjectFiles.md`,
  sección 12.
- La base de datos vive siempre fuera del repositorio
  (`get_user_database_path()`, por defecto
  `%LOCALAPPDATA%/CargoOptimizer3D/cargo_optimizer.db`), nunca
  hardcodeada, nunca versionada, nunca dentro de OneDrive por defecto.
  No calcular esta ruta en ningún otro punto del código — siempre a
  través de esta función.
- Borrado siempre lógico (`is_active=False`), nunca físico, tanto para
  `product_catalog` como para `loading_space_profiles`: un producto o
  perfil archivado libera su SKU/nombre para que puedan reutilizarse,
  pero la fila sigue existiendo. Los perfiles `is_builtin=True` no
  pueden archivarse ni modificarse directamente
  (`LoadingSpaceProfileRepository.update()` lanza `RepositoryError`);
  solo pueden duplicarse como perfil personalizado.
  Unicidad de SKU/nombre se calcula siempre **solo entre registros
  activos**, nunca como restricción `UNIQUE` a nivel de columna SQLite
  (esa restricción no podría expresar "único entre los activos").
- Ninguna tabla del catálogo tiene claves foráneas hacia otra: cada una
  tiene un ciclo de vida independiente (ver el diagrama en
  `docs/Database.md`). No introducir relaciones `ForeignKey` entre
  `product_catalog`/`loading_space_profiles`/`project_history`/
  `packing_run_history` sin una razón nueva y un ADR.
- `project_history` y `packing_run_history` nunca duplican el
  `.cargo3d` completo ni el layout íntegro de un `PackingResult`: solo
  guardan metadatos agregados (contadores, porcentajes de utilización,
  rutas de archivo, marcas de tiempo). No ampliar estas tablas para
  guardar placements individuales ni estado del visor 3D.
- Cada operación de repositorio abre y cierra su propia sesión corta
  (`DatabaseManager.session_scope()`, un `@contextmanager` que hace
  commit al éxito y rollback+relanza en excepción); nunca se comparte
  una `Session` entre operaciones ni entre hilos. `OptimizationWorker`
  (el `QThread` del motor de packing) nunca abre ni usa una sesión de
  SQLAlchemy — el historial de una ejecución se registra siempre desde
  el hilo de la GUI, después de recibir el `PackingResult`.
- Arranque en **modo limitado** si la base de datos falla al
  inicializarse: `app.py::_initialize_catalog_service()` captura
  `DatabaseError` y construye `MainWindow` con
  `catalog_service=None`. La aplicación **nunca** deja de abrir por un
  fallo de SQLite — `.cargo3d` sigue funcionando sin ningún cambio.
  `MainWindow._apply_catalog_availability()` deshabilita las acciones
  de catálogo/perfiles cuando `self._catalog_service is None`; el aviso
  `QMessageBox.warning` de modo limitado se muestra únicamente cuando
  `catalog_error is not None` (nunca solo porque `catalog_service` sea
  `None`) — mismo criterio que ya se aplicó a los errores de proyecto
  en la fase 7.0, para no romper las pruebas que no pasan
  `catalog_service`.
  El registro de historial (`_record_project_open_history`/
  `_record_project_save_history`/`_record_run_history`) nunca puede
  impedir abrir, guardar o completar una optimización: cualquier
  `DatabaseError` durante el registro se captura, se añade como aviso
  al panel de registro, y la operación principal continúa.
- `DatabaseManager.backup()` usa la API nativa
  `sqlite3.Connection.backup(...)`, nunca una copia de archivo en
  crudo — es segura con la base de datos en uso, especialmente bajo
  `journal_mode=WAL`. No sustituir esto por `shutil.copy` sin una razón
  documentada.
- Búsquedas y comprobaciones de unicidad son explícitamente
  insensibles a mayúsculas/minúsculas (`func.lower(...)`), nunca
  `COLLATE NOCASE` a nivel de columna, precisamente porque la
  unicidad debe evaluarse solo entre registros activos.
- El esquema (`schema_metadata`, clave `schema_version`) solo
  reconoce la versión `"1"` hoy. Una versión desconocida
  (`_ensure_supported_schema_version`) es siempre un error claro
  (`DatabaseMigrationError`) que detiene la operación — nunca se
  adivina ni se modifica la base de datos para "adaptarla". No
  introducir un framework de migraciones complejo (Alembic u otro)
  sin necesidad real demostrada.
- Nunca construir SQL a partir de texto de usuario: todas las
  consultas usan la construcción de expresiones de SQLAlchemy
  (parámetros), nunca interpolación de cadenas.

## Reglas de trabajo con el asistente

- Antes de escribir código en una fase nueva: diseñar, documentar,
  proponer alternativas y justificar decisiones técnicas. Registrar
  las decisiones significativas como ADR en `docs/ADR/`.
- Si una decisión del usuario implica una mala decisión de
  arquitectura, decirlo explícitamente y explicar por qué, antes de
  implementarla.
- No sobrearquitecturar: preferir una base pequeña, limpia y
  totalmente funcional sobre abstracciones especulativas. No crear
  paquetes, interfaces ni patrones para necesidades hipotéticas.
- Nunca dejar archivos incompletos, imports rotos ni pseudocódigo.
