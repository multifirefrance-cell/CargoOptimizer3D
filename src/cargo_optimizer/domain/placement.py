"""Placement: colocación concreta de una instancia de LoadUnit en el espacio.

No contiene lógica de detección de colisiones: eso pertenece al motor
geométrico (fase 2.2 del roadmap, ver docs/Roadmap.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.position import Position3D


@dataclass(frozen=True, slots=True)
class Placement:
    """Dónde y cómo queda colocada una instancia concreta de un LoadUnit.

    ``instance_number`` identifica cuál de las unidades físicas
    solicitadas (1..N) es esta colocación; ``sequence_number`` es el
    orden en el que el algoritmo de packing la colocó.
    """

    load_unit_id: UUID
    instance_number: int
    position: Position3D
    orientation: Orientation
    sequence_number: int

    def __post_init__(self) -> None:
        if self.instance_number < 1:
            raise DomainValidationError("instance_number debe ser mayor o igual que 1.")
        if self.sequence_number < 1:
            raise DomainValidationError("sequence_number debe ser mayor o igual que 1.")

    @property
    def x_cm(self) -> float:
        return self.position.x_cm

    @property
    def y_cm(self) -> float:
        return self.position.y_cm

    @property
    def z_cm(self) -> float:
        return self.position.z_cm

    @property
    def length_cm(self) -> float:
        return self.orientation.x_size_cm

    @property
    def width_cm(self) -> float:
        return self.orientation.y_size_cm

    @property
    def height_cm(self) -> float:
        return self.orientation.z_size_cm

    @property
    def max_x_cm(self) -> float:
        return self.x_cm + self.length_cm

    @property
    def max_y_cm(self) -> float:
        return self.y_cm + self.width_cm

    @property
    def max_z_cm(self) -> float:
        return self.z_cm + self.height_cm

    @property
    def volume_cm3(self) -> float:
        return self.length_cm * self.width_cm * self.height_cm
