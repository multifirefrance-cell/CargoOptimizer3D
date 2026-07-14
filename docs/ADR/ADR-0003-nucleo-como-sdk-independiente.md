# ADR-0003: El núcleo (domain + application) es un SDK sin dependencia de UI

## Estado

Aceptada — 2026-07-14

## Contexto

El objetivo de negocio es que CargoOptimizer3D pueda distribuirse como
Desktop, API REST, SDK embebido en un ERP, servicio o aplicación web,
sin reescribir el motor. Esto solo es posible si el motor (`domain` +
`application`) puede usarse con una sentencia como:

```python
from cargo_optimizer import Optimizer
```

sin que esa importación arrastre PySide6, SQLAlchemy, openpyxl,
ReportLab o VTK.

## Decisión

- `cargo_optimizer/__init__.py` no importa nunca `presentation` ni
  `infrastructure`. Cuando exista un `Optimizer` público (fase 4), se
  reexportará desde `domain`/`application` en `__init__.py`, de forma
  que `import cargo_optimizer` jamás dispare la carga de Qt.
- `presentation` y `infrastructure` son las únicas capas autorizadas a
  importar bibliotecas externas de UI, persistencia, ofimática o
  visualización. `domain` y `application` no importan ninguna.
- El punto de entrada `python -m cargo_optimizer` (en `__main__.py`) sí
  importa `presentation.desktop`, pero eso ocurre solo al ejecutar la
  aplicación de escritorio, nunca al hacer `import cargo_optimizer`
  como biblioteca.

## Consecuencias

**Beneficios:**
- Un backend de API REST futuro puede depender de `cargo-optimizer3d`
  como librería sin instalar PySide6 ni ninguna dependencia de
  escritorio.
- Los tests del motor de optimización no necesitan un entorno gráfico
  ni un display virtual.

**Costes / riesgos aceptados:**
- Ninguna clase de dominio o aplicación puede "atajar" e importar Qt
  para conveniencia (p. ej. usar `QRect` como estructura de datos). Se
  verifica con import-linter (ADR-0004).
