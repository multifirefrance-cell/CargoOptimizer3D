# Arquitectura de CargoOptimizer3D

Este documento describe la arquitectura definitiva congelada al cierre
de la fase 1 (infraestructura + arquitectura). Las decisiones aquí
resumidas están justificadas en detalle en `docs/ADR/`.

## Visión

CargoOptimizer3D debe poder distribuirse como aplicación de escritorio,
API REST, SDK embebido en un ERP, servicio o aplicación web, **sin
reescribir el motor**. Esto se consigue separando estrictamente el
motor de negocio (dominio + aplicación) de cualquier mecanismo de
entrega o cualquier detalle técnico externo.

## Capas y regla de dependencia

```
┌─────────────────────────────────────────────────────────┐
│ presentation   (desktop hoy; api / web en el futuro)     │
├─────────────────────────────────────────────────────────┤
│ infrastructure (SQLite, Excel, PDF, VTK — fases 5/7/8)   │
├─────────────────────────────────────────────────────────┤
│ application    (casos de uso, orquestación, puertos)     │
├─────────────────────────────────────────────────────────┤
│ optimization   (motor de optimización — fase 4.1, implementado)   │
├─────────────────────────────────────────────────────────┤
│ rules          (motor de reglas de negocio — fase 3)     │
├─────────────────────────────────────────────────────────┤
│ geometry       (cálculos espaciales — fase 2.2)          │
├─────────────────────────────────────────────────────────┤
│ domain         (LoadingSpace, LoadUnit, invariantes)      │
└─────────────────────────────────────────────────────────┘
```

Una capa solo puede importar las que están por debajo de ella en el
diagrama. `domain` no importa nada del propio proyecto. Esta regla se
verifica automáticamente con `import-linter` (ADR-0004); no es solo una
convención documental.

### `domain`

Entidades y reglas de negocio puras: `LoadingSpace`, `LoadUnit` y sus
invariantes geométricas y de negocio. Sin dependencias externas. Es el
paquete más estable del sistema: cambia solo cuando cambia el
modelo de negocio, nunca por un cambio de framework de UI o de base de
datos.

### `application`

Casos de uso (p. ej. "optimizar un plan de carga para un Loading
Space dado un conjunto de Load Units") y los puertos — interfaces
Python (probablemente `Protocol` o `ABC` mínimas, a decidir en su
fase) que `infrastructure` implementará: repositorios de persistencia,
exportadores, proveedores de render. Depende solo de `domain`.

### `infrastructure`

Adaptadores concretos de los puertos definidos en `application`:
SQLAlchemy/SQLite (fase 7), openpyxl/ReportLab (fase 8), VTK (fase 5).
Vacío hasta que llegue cada fase. Depende de `application` y `domain`.

### `presentation`

Mecanismos de entrega. Hoy contiene `presentation/desktop` (PySide6).
En el futuro, `presentation/api` (REST) o `presentation/web` se añaden
como hermanos, sin tocar el código de escritorio existente. Es la
única capa, junto con `infrastructure`, donde se permite importar
bibliotecas externas (Qt en este caso). Los recursos propios de un
adaptador de presentación (iconos, `.qrc`, plantillas HTML) viven
dentro de ese adaptador — p. ej. `presentation/desktop/resources/` —
nunca en un directorio compartido a nivel de proyecto, porque no son un
recurso del SDK sino de un mecanismo de entrega concreto.

Desde la fase 5.0, `presentation/desktop/` tiene esta forma:

```
presentation/desktop/
├── app.py               # arranque: QApplication, tema, MainWindow
├── main_window.py        # MainWindow: menús, toolbar, splitters, dock, status bar
├── icons.py               # carga de resources/icons/*.svg como QIcon
├── style.py                # paletas claro/oscuro + QSS (aspecto industrial)
├── settings.py              # AppSettings: wrapper de QSettings, claves centralizadas
├── models/
│   └── product_table_model.py  # QAbstractTableModel sobre list[LoadUnit]
├── panels/
│   ├── project_tree_panel.py
│   ├── loading_space_form_panel.py
│   ├── product_table_panel.py
│   ├── results_panel.py
│   └── viewport_3d_placeholder.py
└── resources/icons/*.svg
```

Todos los modelos y paneles pueden importar `cargo_optimizer.domain`
(está por debajo de `presentation` en la regla de dependencia) — de
hecho `ProductTableModel` y `LoadingSpaceFormPanel` construyen
`LoadUnit`/`LoadingSpace` reales, no una copia paralela del esquema de
dominio. Ninguno importa `cargo_optimizer.optimization` todavía: la
fase 5.0 construye la interfaz sin invocar `PackingEngine` (ver
`docs/OptimizationEngine.md`); conectarlo es la fase 5.1.

## Motores de negocio: geometry, rules, optimization

```
src/cargo_optimizer/
├── domain/
├── geometry/       # fase 2.2 — implementado, depende solo de domain
├── rules/          # fase 3 — implementado, depende de domain y geometry
├── optimization/   # fase 4.1 — implementado, depende de domain, geometry y rules
├── application/    # orquesta domain + geometry + rules + optimization (fase 6+)
├── infrastructure/
└── presentation/
```

`geometry` (fase 2.2), `rules` (fase 3) y `optimization` (fase 4.1) ya
existen. `geometry`: cajas ortoédricas, límites, colisiones, soporte
físico, puntos candidatos y validación de layouts — ver
`docs/GeometryEngine.md` y ADR-0006. `rules`: motor de reglas de
negocio puro y determinista (orientaciones permitidas, extintores,
apilamiento, fragilidad, peso) que responde si una colocación es
válida sin decidir dónde colocar nada — ver `docs/RulesEngine.md` y
ADR-0007. `optimization`: motor de empaquetado real, con la estrategia
`greedy_extreme_point_v1` (`GreedyExtremePointStrategy`) — ver
`docs/OptimizationEngine.md` (implementación real),
`docs/OptimizationEngineDesign.md` y
`docs/GreedyLayerStrategyDesign.md` (diseño original de fase 4.0,
conservados como historial), ADR-0008 y ADR-0009. La fase 4.2 optimizó
el rendimiento interno de `optimization` (caché incremental de
bounding box, poda de candidatos) sin cambiar esta estructura ni la API
pública — ver `docs/OptimizerPerformance.md`.

Se crean como hermanos de `domain` (no como subpaquetes de `domain` ni
de `application`) porque son subsistemas sustanciales con algoritmos
propios (bin packing, resolución de restricciones), no simples
entidades ni casos de uso de orquestación. Mezclar esta decisión con la
lista de capas (`domain`/`geometry`/`rules`/`optimization`/`application`/`infrastructure`/`presentation`)
sería confundir dos ejes de descomposición distintos — ver ADR-0001,
sección de rechazo explícito de esa alternativa.

## El núcleo como SDK

`domain` + `optimization` (+ `application` cuando exista) forman el
SDK público del proyecto. Ya funciona, sin ninguna dependencia de UI
instalada:

```python
from cargo_optimizer import PackingEngine, PackingRequest
```

Ver ADR-0003 para el detalle de esta garantía y cómo se protege.

## Verificación de la arquitectura

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\lint-imports.exe                    # import-linter — regla de capas
.\.venv\Scripts\python.exe -m pytest
```
