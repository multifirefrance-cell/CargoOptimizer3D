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
- **`infrastructure`**: adaptadores concretos (SQLAlchemy, openpyxl,
  ReportLab, VTK) que implementan los puertos de `application`.
- **`presentation`**: mecanismos de entrega (`presentation/desktop`
  hoy con PySide6; `presentation/api` o web en el futuro, como
  hermanos, sin tocar el código existente).

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
- VTK para visualización 3D (fase 5, aún no implementada).
- SQLite + SQLAlchemy para persistencia (fase 7, aún no implementada).
- openpyxl para Excel y ReportLab para PDF (fase 8, aún no
  implementadas).
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
├── infrastructure/  # Adaptadores concretos: SQLite, Excel, PDF, VTK (fases posteriores).
└── presentation/
    └── desktop/     # Aplicación de escritorio PySide6. Solo presentación.
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
   6. Visualización 3D — 7. Persistencia — 8. Reportes — 9. Integración
   ERP — 10. Versión comercial.

La fase 2 original ("Motor geométrico") se dividió en 2.1 (modelo de
dominio puro) y 2.2 (motor geométrico) para poder completar el modelo
de dominio sin implementar todavía colisiones ni packing. Ver
`docs/Roadmap.md`, sección "Nota sobre la numeración de la fase 2". La
fase 4 se dividió igual, en 4.0 (diseño puro) y 4.1 (implementación),
por el mismo motivo: no crear `optimization/` antes de haber diseñado
qué contendrá. La fase 5 se renumeró de "5 = Visualización 3D, 6 =
Interfaz" a "5.0/5.1 = Interfaz, 6 = Visualización 3D" al construir la
interfaz antes que VTK — ver `docs/Roadmap.md`, sección "Nota sobre la
numeración de las fases 5 y 6".

Estado actual: **base profesional de la interfaz de escritorio
construida** (fin de fase 5.0). `presentation/desktop` tiene una
`MainWindow` real (menús, toolbar, paneles acoplables, formulario de
Loading Space, tabla de productos, panel de resultados vacío,
placeholder de vista 3D, tema claro/oscuro, persistencia de interfaz
vía `QSettings`) — ver `docs/Architecture.md`, sección `presentation`.
El motor (`domain`/`geometry`/`rules`/`optimization`) queda intacto y
sin conectar todavía: `PackingEngine` no se invoca desde la interfaz
hasta la fase 5.1. No implementar todavía VTK, SQLite, Excel, PDF,
importación/exportación real, animaciones, Undo/Redo, ni volver a
tocar `domain`/`geometry`/`rules`/`optimization` salvo bug objetivo y
demostrable, hasta que se indique explícitamente. Ver `docs/Roadmap.md`
para el detalle fase a fase.

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
completo de la estructura de `presentation/desktop/` construida en la
fase 5.0.

- `presentation/desktop` no invoca `PackingEngine` todavía: ninguna
  acción de menú/toolbar ejecuta el motor de optimización. Conectarlo
  es exactamente el alcance de la fase 5.1, no antes.
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
- Persistencia de interfaz exclusivamente vía `QSettings`
  (`presentation/desktop/settings.py::AppSettings`), nunca SQLite ni
  otro almacenamiento: eso pertenece a la fase 7 (persistencia de
  proyectos), un concepto distinto de "recordar el estado de la
  ventana".
- `Viewport3DPlaceholder` no importa VTK ni ninguna biblioteca de
  render 3D: es un `QWidget` de marcador de posición hasta la fase 6.
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
