# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Este proyecto aún no ha alcanzado la versión 1.0; el versionado 0.x
puede incluir cambios estructurales entre versiones menores.

## [0.4.0] - 2026-07-14

### Added

- Motor geométrico determinista (fase 2.2 del roadmap): paquete
  `cargo_optimizer.geometry`, hermano de `domain`, dependiendo
  únicamente de él (verificado con `import-linter`).
- `AxisAlignedBox` con `contains_point`, `contains_box`, `intersects`,
  `overlaps`, `touches` e `intersection_volume_cm3`; `box_from_placement`.
- `fits_inside_loading_space` / `validate_box_inside_loading_space`
  (`geometry/bounds.py`).
- Detección de colisiones O(n²): `boxes_overlap`,
  `placement_overlaps_any`, `find_overlapping_placements`
  (`geometry/collision.py`); tocarse no cuenta como colisión.
- `Rectangle2D` y `union_area_cm2` (unión de rectángulos 2D por
  compresión de coordenadas, sin dependencias externas).
- Soporte físico básico: `support_area_cm2`, `support_ratio`,
  `is_supported`, sin doble conteo de áreas de soporte solapadas.
- `generate_candidate_positions`: puntos candidatos deterministas
  (origen + extremos X/Y/Z de cada Placement), sin heurísticas de
  optimización todavía.
- `validate_layout`: detecta cajas fuera de límites, superposiciones,
  falta de soporte, e `instance_number`/`sequence_number` duplicados.
- `GEOMETRY_EPSILON_CM` (1e-9 cm), tolerancia única centralizada para
  todas las comparaciones geométricas.
- `docs/GeometryEngine.md` y
  `docs/ADR/ADR-0006-motor-geometrico-tolerancia-y-contacto.md`.
- 68 pruebas unitarias del motor geométrico (141 en total con las de
  dominio).

## [0.3.0] - 2026-07-14

### Added

- Modelo de dominio puro (fase 2.1 del roadmap): `Dimensions3D`,
  `Orientation`, `OrientationCode`, `Position3D`, `LoadingSpace` (con
  perfiles orientativos de contenedor 20 ft / 40 ft / 40 ft High
  Cube), `LoadUnit`, `Placement`, `UnpackedUnit`, `PackingResult`,
  `CargoProject` y la jerarquía de excepciones de dominio.
- Enums de dominio con valores string estables (`LoadingSpaceCategory`,
  `DoorPosition`, `PackageType`, `ExtinguisherAgent`,
  `OrientationCode`), heredando de `enum.StrEnum`.
- `docs/DomainModel.md`: sistema de coordenadas, invariantes, diagrama
  Mermaid y distinciones conceptuales (quantity vs. units_per_package
  vs. total_requested_units; peso nominal del extintor vs. peso bruto
  del empaque).
- `docs/ADR/ADR-0005-inmutabilidad-y-enums-estables.md`.
- 73 pruebas unitarias del modelo de dominio.
- `from cargo_optimizer import LoadingSpace, LoadUnit` (y el resto del
  modelo de dominio) disponible como API pública del SDK.

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
