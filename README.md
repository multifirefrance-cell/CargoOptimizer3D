# CargoOptimizer3D

Software profesional de optimización de carga 3D (3D Bin Packing) para
cualquier espacio de carga: contenedores marítimos, camiones, furgones,
vans, semirremolques, bodegas, plataformas, vagones, aviones o cualquier
espacio definido por el usuario.

## Conceptos de dominio

- **Loading Space**: cualquier espacio de carga (no está limitado a
  "contenedor").
- **Load Unit**: cualquier unidad a cargar — caja, pallet, cilindro,
  tambor, bobina, tubo, maquinaria, carga irregular o grupo de cajas
  (no se llama "producto").

## Arquitectura

Arquitectura en capas (Clean Architecture / Hexagonal): el motor de
negocio (`domain` + `application`) no depende de ninguna biblioteca de
UI, persistencia, ofimática ni visualización, y puede reutilizarse
desde una aplicación de escritorio, una API REST, un ERP o una futura
aplicación web, sin reescribirse.

```
src/cargo_optimizer/
├── domain/          # Entidades y reglas de negocio puras. Sin dependencias externas.
├── application/     # Casos de uso, orquestación, puertos hacia infraestructura.
│                    #   MultiSpaceAssignmentEngine: asignación automática multi-espacio.
├── infrastructure/  # Adaptadores concretos: persistence/ (proyectos .cargo3d, JSON),
│                    #   database/ (catálogo SQLite/SQLAlchemy), excel/ (import/export .xlsx),
│                    #   pdf/ (informes PDF, ReportLab).
└── presentation/
    └── desktop/     # Aplicación de escritorio (PySide6). Incluye viewer/ (visor 3D).
```

La regla de dependencia (una capa solo importa las que están por
debajo: `presentation → infrastructure → application → domain`) se
verifica automáticamente con `import-linter`.

Ver [docs/Architecture.md](docs/Architecture.md) para el detalle
completo, [docs/Roadmap.md](docs/Roadmap.md) para las fases, y
[docs/ADR/](docs/ADR/) para el historial de decisiones. Ver
[CLAUDE.md](CLAUDE.md) para las reglas permanentes del proyecto.

## Requisitos

- Python 3.12+
- Windows (objetivo principal actual)

## Instalación (entorno de desarrollo)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Ejecutar la aplicación

```powershell
.\.venv\Scripts\python.exe -m cargo_optimizer
```

## Desarrollo

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\lint-imports.exe
.\.venv\Scripts\python.exe -m pytest
```

## Estado del proyecto

Fin de fase 9.1: motor de optimización, interfaz de escritorio, visor
3D, persistencia de proyectos (`.cargo3d`, JSON versionado), catálogo
reutilizable de productos/perfiles respaldado por SQLite,
importación/exportación profesional de Excel (`.xlsx`), automatización
del flujo Excel (mapeo de columnas con perfiles reutilizables, vista
previa, importación parcial, resolución de duplicados, arrastrar y
soltar, importación masiva, informe de importación, exportación
avanzada) y generación de informes PDF profesionales (cinco tipos de
informe, integración opcional con la captura del visor 3D,
configuración de empresa/cliente/colores/marca de agua) ya
implementados — ver `docs/Roadmap.md` para el detalle fase a fase,
`docs/ProjectFiles.md` para el formato de archivo de proyecto,
`docs/Database.md` para el catálogo SQLite (productos, perfiles de
Loading Space, perfiles de mapeo de Excel e historial básico),
`docs/Excel.md` para el importador/exportador de Excel (plantillas
oficiales en `examples/templates/`), `docs/ExcelAutomation.md` para la
automatización del flujo, y `docs/PdfReports.md` para el sistema de
informes PDF (`infrastructure/pdf/`, ReportLab).

Desde la fase 10.1, el trabajo posterior se rige por
[docs/ProductBacklog.md](docs/ProductBacklog.md) (backlog comercial
priorizado por valor, organizado en EPICs con un ID estable por ítem),
no por la numeración secuencial de fases. Primer ítem implementado:
`OPT-01`, asignación automática multi-espacio
(`application.MultiSpaceAssignmentEngine` — ver
[docs/MultiSpaceAssignment.md](docs/MultiSpaceAssignment.md)); la
integración con la interfaz de escritorio queda para un encargo
posterior. La integración ERP se implementará en una fase posterior.
