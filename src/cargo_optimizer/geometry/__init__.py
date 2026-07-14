"""Motor geométrico de CargoOptimizer3D.

Realiza cálculos espaciales deterministas sobre las entidades del
dominio: cajas ortoédricas, límites, colisiones, soporte físico,
puntos candidatos y validación de layouts completos. El dominio
(``cargo_optimizer.domain``) describe objetos y estados; este paquete
calcula sobre ellos.

Regla de dependencia (no negociable): este paquete depende únicamente
de ``cargo_optimizer.domain``. Nunca importa ``application``,
``infrastructure``, ``presentation``, ni ninguna biblioteca externa
(PySide6, SQLAlchemy, openpyxl, ReportLab, VTK). Verificado
automáticamente con import-linter (ver ``pyproject.toml`` y
``docs/ADR/ADR-0006``).

No implementa todavía: algoritmo de packing, heurísticas de
optimización, reglas específicas de negocio (p. ej. horizontalidad
obligatoria de extintores), visualización, persistencia ni reportes.
"""

from __future__ import annotations

from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.geometry.candidate_points import generate_candidate_positions
from cargo_optimizer.geometry.collision import (
    boxes_overlap,
    find_overlapping_placements,
    placement_overlaps_any,
)
from cargo_optimizer.geometry.layout_validation import (
    LayoutValidationIssue,
    LayoutValidationResult,
    validate_layout,
)
from cargo_optimizer.geometry.support import is_supported, support_ratio

__all__ = [
    "AxisAlignedBox",
    "LayoutValidationIssue",
    "LayoutValidationResult",
    "box_from_placement",
    "boxes_overlap",
    "find_overlapping_placements",
    "fits_inside_loading_space",
    "generate_candidate_positions",
    "is_supported",
    "placement_overlaps_any",
    "support_ratio",
    "validate_layout",
]
