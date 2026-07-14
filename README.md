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

El proyecto separa un **núcleo (SDK)** sin dependencias de interfaz de
una **aplicación de escritorio** construida sobre PySide6. El núcleo
está pensado para ser reutilizado desde una API REST, un ERP o una
futura aplicación web/móvil.

```
src/cargo_optimizer/
├── core/     # Lógica de dominio y negocio (SDK). Sin dependencias de UI.
└── ui/       # Aplicación de escritorio (PySide6). Solo presentación.
```

Ver [CLAUDE.md](CLAUDE.md) para las reglas de arquitectura permanentes
del proyecto.

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
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest
```

## Estado del proyecto

Fase actual: infraestructura base. El motor de optimización, las
reglas de restricciones, la visualización 3D, la persistencia y los
reportes se implementarán en fases posteriores (ver `CLAUDE.md`).
