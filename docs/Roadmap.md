# Roadmap de CargoOptimizer3D

Cada fase se diseña y documenta antes de escribir código (ver
`CLAUDE.md`, sección "Reglas de trabajo con el asistente"). Ninguna
fase se adelanta a la anterior.

| Fase | Nombre | Paquete(s) que crea o rellena | Estado |
|---|---|---|---|
| 0 | Diseño completo | — | Completada |
| 1 | Arquitectura | `domain`, `application`, `infrastructure`, `presentation` (estructura, vacíos donde aplique) | **Completada** |
| 2 | Motor geométrico | `geometry` (nuevo, hermano de `domain`) | Pendiente |
| 3 | Motor de restricciones | `rules` (nuevo, hermano de `domain`) | Pendiente |
| 4 | Motor de optimización | `optimization` (nuevo, hermano de `domain`); primer caso de uso real en `application` | Pendiente |
| 5 | Visualización 3D | `infrastructure` (adaptador VTK) | Pendiente |
| 6 | Interfaz | `presentation/desktop` (pantallas reales) | Pendiente |
| 7 | Persistencia | `infrastructure` (adaptador SQLAlchemy/SQLite) | Pendiente |
| 8 | Reportes | `infrastructure` (adaptadores openpyxl/ReportLab) | Pendiente |
| 9 | Integración ERP | `presentation` (nuevo adaptador, p. ej. `presentation/api`) | Pendiente |
| 10 | Versión comercial | — | Pendiente |

## Regla para crear `geometry`, `rules` y `optimization`

Estos paquetes **no se crean por adelantado**. Se crean como paquetes
de nivel superior, hermanos de `domain`, únicamente cuando comienza su
fase de diseño correspondiente (ver `docs/Architecture.md`, sección
"Motores de negocio"). Cada uno debe:

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

## Estado actual

Fin de fase 1: infraestructura y arquitectura congeladas. No se ha
escrito ninguna línea de lógica de negocio, geometría, reglas,
optimización, persistencia, exportación ni visualización 3D. La
siguiente sesión de desarrollo debe empezar por el diseño de la fase 2
(motor geométrico) antes de escribir código.
