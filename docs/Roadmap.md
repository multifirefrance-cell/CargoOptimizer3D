# Roadmap de CargoOptimizer3D

Cada fase se diseña y documenta antes de escribir código (ver
`CLAUDE.md`, sección "Reglas de trabajo con el asistente"). Ninguna
fase se adelanta a la anterior.

| Fase | Nombre | Paquete(s) que crea o rellena | Estado |
|---|---|---|---|
| 0 | Diseño completo | — | Completada |
| 1 | Arquitectura | `domain`, `application`, `infrastructure`, `presentation` (estructura, vacíos donde aplique) | **Completada** |
| 2.1 | Modelo de dominio puro | `domain` (entidades y value objects: `Dimensions3D`, `Orientation`, `LoadingSpace`, `LoadUnit`, `Position3D`, `Placement`, `UnpackedUnit`, `PackingResult`, `CargoProject`) | **Completada** |
| 2.2 | Motor geométrico (geometría, colisiones, soporte) | `geometry` (hermano de `domain`) | **Completada** |
| 3 | Motor de restricciones | `rules` (hermano de `domain`) | **Completada** |
| 4 | Motor de optimización | `optimization` (nuevo, hermano de `domain`); primer caso de uso real en `application` | Pendiente |
| 5 | Visualización 3D | `infrastructure` (adaptador VTK) | Pendiente |
| 6 | Interfaz | `presentation/desktop` (pantallas reales) | Pendiente |
| 7 | Persistencia | `infrastructure` (adaptador SQLAlchemy/SQLite) | Pendiente |
| 8 | Reportes | `infrastructure` (adaptadores openpyxl/ReportLab) | Pendiente |
| 9 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 10 | Versión comercial | — | Pendiente |

## Regla para crear `optimization` (`geometry` y `rules` ya existen)

`geometry` se creó en la fase 2.2 (ver `docs/GeometryEngine.md` y
ADR-0006). `rules` se creó en la fase 3 (ver `docs/RulesEngine.md` y
ADR-0007). `optimization` **no se crea por adelantado**: se crea como
paquete de nivel superior, hermano de `domain`, únicamente cuando
comienza su fase de diseño (ver `docs/Architecture.md`, sección
"Motores de negocio"). Debe:

1. Diseñarse y documentarse antes de escribir código (una entrada en
   `docs/ADR/` si la decisión es significativa).
2. Depender únicamente de `domain` y de los motores de fases
   anteriores ya existentes (p. ej. `rules` puede depender de
   `geometry`, pero `geometry` nunca de `rules`).
3. Quedar reflejado en el contrato de `import-linter` en
   `pyproject.toml` en cuanto exista.

## Regla para crear adaptadores de `infrastructure` y `presentation`

- Un adaptador de `infrastructure` (SQLite, Excel, PDF, VTK) se crea
  como subpaquete de `infrastructure` en la fase que lo introduce
  (p. ej. `infrastructure/persistence/`, `infrastructure/reporting/`).
- Un nuevo mecanismo de entrega (API REST, web) se crea como subpaquete
  hermano de `presentation/desktop`, p. ej. `presentation/api/`, sin
  modificar el código de escritorio existente.

## Nota sobre la numeración de la fase 2

La fase 2 original ("Motor geométrico") se dividió en dos entregas:
**2.1 Modelo de dominio puro** (completada en esta sesión) y **2.2
Motor geométrico** (colisiones, packing — pendiente). Se optó por esta
subdivisión, en vez de renumerar en cascada las fases 3-10 ya
documentadas en `CLAUDE.md` y `docs/Architecture.md`, para no romper
referencias existentes por un ajuste que es de alcance, no de
arquitectura.

## Estado actual

Fin de fase 3: motor de reglas completado (orientaciones permitidas,
reglas críticas de extintores individuales y grupales, apilamiento,
fragilidad, peso soportado, peso del Loading Space, evaluación
compuesta `evaluate_candidate_placement`, fachada `RulesEngine`), con
240 pruebas unitarias en verde (73 de dominio + 68 de geometría + 99 de
reglas). `rules` depende de `domain` siempre y de `geometry` solo
donde una regla necesita información espacial, verificado por
`import-linter`. No se ha escrito ninguna línea de algoritmo de
packing, heurísticas de optimización, persistencia, exportación ni
visualización 3D. La siguiente sesión de desarrollo debe empezar por
el diseño de la fase 4 (motor de optimización) antes de escribir
código.
