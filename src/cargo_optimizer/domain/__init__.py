"""Dominio de CargoOptimizer3D.

Contiene las entidades y reglas de negocio puras del sistema: Loading
Space, Load Unit y sus invariantes. Es el núcleo del SDK.

Regla de dependencia (no negociable): este paquete no importa nada de
``application``, ``infrastructure`` ni ``presentation``, ni de ninguna
biblioteca externa de UI, persistencia, ofimática o visualización
(PySide6/Qt, SQLAlchemy, openpyxl, ReportLab, VTK). Es la capa más
interna: todo lo demás depende de ella, ella no depende de nada. Esta
regla se verifica automáticamente con import-linter (ver
``pyproject.toml`` y ``docs/ADR/ADR-0004``).
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    DoorPosition,
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.exceptions import DomainError, DomainValidationError, DuplicateSkuError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.project import CargoProject
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit

__all__ = [
    "CargoProject",
    "Dimensions3D",
    "DomainError",
    "DomainValidationError",
    "DoorPosition",
    "DuplicateSkuError",
    "ExtinguisherAgent",
    "LoadUnit",
    "LoadingSpace",
    "LoadingSpaceCategory",
    "Orientation",
    "OrientationCode",
    "PackageType",
    "PackingResult",
    "Placement",
    "Position3D",
    "UnpackedUnit",
]
