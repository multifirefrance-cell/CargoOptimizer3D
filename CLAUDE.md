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
presentation  →  infrastructure  →  application  →  domain
  (externa)                                        (interna)
```

- **`domain`**: entidades y reglas de negocio puras (`LoadingSpace`,
  `LoadUnit`, invariantes). No depende de nada, ni del propio proyecto
  ni de bibliotecas externas de UI/persistencia/ofimática/visualización.
- **`application`**: casos de uso, orquestación, puertos (interfaces)
  hacia `infrastructure`. Depende solo de `domain`.
- **`infrastructure`**: adaptadores concretos (SQLAlchemy, openpyxl,
  ReportLab, VTK) que implementan los puertos de `application`.
- **`presentation`**: mecanismos de entrega (`presentation/desktop`
  hoy con PySide6; `presentation/api` o web en el futuro, como
  hermanos, sin tocar el código existente).

Esta regla se verifica automáticamente con `import-linter` (contrato
`layers` en `pyproject.toml`), no es solo documentación. Detalle
completo y justificación en `docs/Architecture.md` y
`docs/ADR/ADR-0001-arquitectura-en-capas.md`.

**`geometry`, `rules` y `optimization` no existen todavía como
paquetes.** Se crean como paquetes de nivel superior, hermanos de
`domain` (dependiendo únicamente de `domain` y de los motores de fases
anteriores), únicamente cuando comience su fase de diseño
correspondiente (fases 2.2, 3 y 4). No crearlos por adelantado: ver
`docs/Roadmap.md`.

El núcleo (`domain` + `application` + los motores cuando existan) es
un SDK independiente: debe poder usarse con
`from cargo_optimizer import Optimizer` sin ninguna dependencia de UI
instalada (ADR-0003).

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
├── application/     # Casos de uso, orquestación, puertos hacia infraestructura.
├── infrastructure/  # Adaptadores concretos: SQLite, Excel, PDF, VTK (fases posteriores).
└── presentation/
    └── desktop/     # Aplicación de escritorio PySide6. Solo presentación.
tests/               # Pruebas, en espejo de la estructura de src/
docs/                # Architecture.md, Roadmap.md, ADR/ — documentación de arquitectura y diseño
examples/            # Proyectos de ejemplo de uso del SDK (poblado desde fase 4)
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
   2.2. Motor geométrico — 3. Motor de restricciones — 4. Motor de
   optimización — 5. Visualización 3D — 6. Interfaz — 7. Persistencia
   — 8. Reportes — 9. Integración ERP — 10. Versión comercial.

La fase 2 original ("Motor geométrico") se dividió en 2.1 (modelo de
dominio puro) y 2.2 (motor geométrico) para poder completar el modelo
de dominio sin implementar todavía colisiones ni packing. Ver
`docs/Roadmap.md`, sección "Nota sobre la numeración de la fase 2".

Estado actual: **modelo de dominio puro completado** (fin de fase 2.1).
No implementar motor geométrico, detección de colisiones, packing 3D,
reglas de restricciones, motor de optimización, visualización 3D,
SQLite, Excel, PDF ni API hasta que se indique explícitamente. Ver
`docs/Roadmap.md` para el detalle fase a fase.

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
  esa lógica pertenece exclusivamente al futuro motor geométrico (fase
  2.2), nunca al modelo de dominio.
- La regla de horizontalidad obligatoria de extintores (no apilar de
  canto) es del motor de restricciones (fase 3), no del dominio. El
  dominio solo deja los campos necesarios preparados.

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
