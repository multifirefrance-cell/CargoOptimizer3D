"""CargoOptimizer3D: SDK de optimización de carga 3D para espacios de carga universales."""

from __future__ import annotations

from cargo_optimizer.domain import (
    CargoProject,
    Dimensions3D,
    LoadingSpace,
    LoadUnit,
    PackingResult,
    Placement,
    Position3D,
)

__version__ = "0.5.0"

__all__ = [
    "CargoProject",
    "Dimensions3D",
    "LoadUnit",
    "LoadingSpace",
    "PackingResult",
    "Placement",
    "Position3D",
    "__version__",
]
