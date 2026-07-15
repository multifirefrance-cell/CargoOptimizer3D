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
   motor de optimización — 4.1. Primer optimizador funcional — 5.
   Visualización 3D — 6. Interfaz — 7. Persistencia — 8. Reportes — 9.
   Integración ERP — 10. Versión comercial.

La fase 2 original ("Motor geométrico") se dividió en 2.1 (modelo de
dominio puro) y 2.2 (motor geométrico) para poder completar el modelo
de dominio sin implementar todavía colisiones ni packing. Ver
`docs/Roadmap.md`, sección "Nota sobre la numeración de la fase 2". La
fase 4 se dividió igual, en 4.0 (diseño puro) y 4.1 (implementación),
por el mismo motivo: no crear `optimization/` antes de haber diseñado
qué contendrá.

Estado actual: **primer optimizador funcional implementado** (fin de
fase 4.1). `optimization` existe, con la estrategia
`greedy_extreme_point_v1` y la fachada `PackingEngine` ya exportada
desde `cargo_optimizer`. No implementar todavía múltiples estrategias,
algoritmo genético, beam search, índice espacial, visualización 3D,
SQLite, Excel, PDF ni API, hasta que se indique explícitamente. Ver
`docs/Roadmap.md` para el detalle fase a fase y
`docs/OptimizationEngine.md` para el rendimiento real medido (peor de
lo estimado en el diseño de fase 4.0 — motivo documentado, no un bug
de `rules`/`geometry`).

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
- **Rendimiento real es O(n³)-ish y notablemente peor de lo estimado
  en el diseño de fase 4.0** (~35 s para 100 instancias, medido). No es
  un bug de `rules` ni `geometry`: es el coste ya anticipado y pospuesto
  a v0.7 (poda de candidatos) / v0.8 (índice espacial). No prometer
  rendimiento distinto al documentado en `docs/OptimizationEngine.md`
  sin haber implementado esas mejoras.

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
