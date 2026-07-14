"""Value object de posición 3D dentro de un Loading Space.

Sistema de coordenadas (ver docs/DomainModel.md): X = largo, Y = ancho,
Z = altura; origen (0, 0, 0) en el suelo, esquina trasera izquierda.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cargo_optimizer.domain.exceptions import DomainValidationError


def _validate_coordinate(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DomainValidationError(f"{name} debe ser numérico.")
    if not math.isfinite(value):
        raise DomainValidationError(f"{name} debe ser un valor finito.")
    if value < 0:
        raise DomainValidationError(f"{name} no puede ser negativo.")


@dataclass(frozen=True, slots=True)
class Position3D:
    """Posición de la esquina de origen de un Placement, en centímetros."""

    x_cm: float
    y_cm: float
    z_cm: float

    def __post_init__(self) -> None:
        _validate_coordinate("x_cm", self.x_cm)
        _validate_coordinate("y_cm", self.y_cm)
        _validate_coordinate("z_cm", self.z_cm)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x_cm, self.y_cm, self.z_cm)
