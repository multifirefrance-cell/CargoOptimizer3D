"""Value object de dimensiones físicas de una caja ortogonal."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations

from cargo_optimizer.domain.exceptions import DomainValidationError


def _validate_positive_dimension(name: str, value: float) -> None:
    if isinstance(value, bool):
        raise DomainValidationError(f"{name} no puede ser un valor booleano.")
    if not isinstance(value, (int, float)):
        raise DomainValidationError(f"{name} debe ser numérico.")
    if math.isnan(value):
        raise DomainValidationError(f"{name} no puede ser NaN.")
    if math.isinf(value):
        raise DomainValidationError(f"{name} no puede ser infinito.")
    if value <= 0:
        raise DomainValidationError(f"{name} debe ser mayor que cero.")


@dataclass(frozen=True, slots=True)
class Dimensions3D:
    """Dimensiones de una caja ortogonal, en centímetros.

    No representa una orientación espacial: es la medida física de la
    caja tal cual, sin asignar todavía qué dimensión va a qué eje. Esa
    asignación la hace ``Orientation``.
    """

    length_cm: float
    width_cm: float
    height_cm: float

    def __post_init__(self) -> None:
        _validate_positive_dimension("length_cm", self.length_cm)
        _validate_positive_dimension("width_cm", self.width_cm)
        _validate_positive_dimension("height_cm", self.height_cm)

    @property
    def volume_cm3(self) -> float:
        return self.length_cm * self.width_cm * self.height_cm

    @property
    def volume_m3(self) -> float:
        return self.volume_cm3 / 1_000_000.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.length_cm, self.width_cm, self.height_cm)

    def all_orientations(self) -> tuple[Dimensions3D, ...]:
        """Las seis permutaciones ortogonales posibles, sin duplicados y en orden determinista.

        Cuando dos o tres dimensiones son iguales, varias permutaciones
        coinciden; se conserva solo la primera aparición, en el orden
        fijo que produce ``itertools.permutations``.
        """
        seen: list[Dimensions3D] = []
        for perm in permutations(self.as_tuple()):
            candidate = Dimensions3D(*perm)
            if candidate not in seen:
                seen.append(candidate)
        return tuple(seen)
