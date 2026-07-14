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
├── infrastructure/  # Adaptadores concretos: SQLite, Excel, PDF, VTK (fases posteriores).
└── presentation/
    └── desktop/     # Aplicación de escritorio (PySide6). Solo presentación.
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

Fin de fase 1: infraestructura y arquitectura congeladas (ver
`docs/Roadmap.md`). El motor geométrico, las reglas de restricciones,
el motor de optimización, la visualización 3D, la persistencia y los
reportes se implementarán en fases posteriores.
