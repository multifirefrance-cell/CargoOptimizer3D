# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Este proyecto aún no ha alcanzado la versión 1.0; el versionado 0.x
puede incluir cambios estructurales entre versiones menores.

## [0.2.0] - 2026-07-14

### Changed

- Arquitectura reestructurada en capas: `core` → `domain`; `ui` →
  `presentation/desktop`. Se añaden `application` e `infrastructure`
  como capas explícitas, vacías hasta sus fases correspondientes. Ver
  `docs/ADR/ADR-0001-arquitectura-en-capas.md`.

### Added

- `import-linter` como dependencia de desarrollo, con contrato de
  capas que verifica automáticamente la regla de dependencia
  (`presentation → infrastructure → application → domain`).
- `docs/ADR/` con las primeras cuatro decisiones de arquitectura
  registradas.
- `docs/Architecture.md` y `docs/Roadmap.md`.
- `examples/` y `userdata/` (vacíos, con propósito documentado).

## [0.1.0] - 2026-07-14

### Added

- Infraestructura base del repositorio: `pyproject.toml` con Ruff,
  Black, Mypy (modo estricto) y Pytest configurados.
- Paquete `cargo_optimizer` instalable en modo editable, ejecutable
  vía `python -m cargo_optimizer`.
- Aplicación de escritorio mínima con PySide6 (ventana principal).
- Primer test de humo.
