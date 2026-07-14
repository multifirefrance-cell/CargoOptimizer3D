"""LoadingSpace: entidad que representa cualquier espacio de carga.

Universal por diseño (ver ADR-0002): un contenedor marítimo es solo una
de las categorías posibles, nunca el concepto genérico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError

_PROFILE_NOTE = "Perfil orientativo. Las dimensiones reales varían según fabricante y operador."


@dataclass(frozen=True, slots=True)
class LoadingSpace:
    """Un espacio de carga concreto: contenedor, camión, bodega, rack, etc.

    No asume nunca que representa específicamente un contenedor
    marítimo: ``category`` es solo metadata descriptiva.
    """

    name: str
    category: LoadingSpaceCategory
    internal_dimensions: Dimensions3D
    door_position: DoorPosition = DoorPosition.REAR
    max_weight_kg: float | None = None
    notes: str = ""
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("El nombre del Loading Space no puede estar vacío.")
        if self.max_weight_kg is not None and (
            isinstance(self.max_weight_kg, bool) or self.max_weight_kg <= 0
        ):
            raise DomainValidationError(
                "max_weight_kg debe ser mayor que cero cuando se especifica."
            )
        object.__setattr__(self, "notes", str(self.notes))

    @property
    def capacity_volume_cm3(self) -> float:
        return self.internal_dimensions.volume_cm3

    @property
    def capacity_volume_m3(self) -> float:
        return self.internal_dimensions.volume_m3

    @classmethod
    def standard_20ft_container(
        cls, name: str = "Contenedor 20 pies (perfil estándar)"
    ) -> LoadingSpace:
        """Perfil orientativo de un contenedor marítimo estándar de 20 pies (dry van)."""
        return cls(
            name=name,
            category=LoadingSpaceCategory.CONTAINER,
            internal_dimensions=Dimensions3D(589.0, 235.0, 239.0),
            door_position=DoorPosition.REAR,
            max_weight_kg=28180.0,
            notes=_PROFILE_NOTE,
        )

    @classmethod
    def standard_40ft_container(
        cls, name: str = "Contenedor 40 pies (perfil estándar)"
    ) -> LoadingSpace:
        """Perfil orientativo de un contenedor marítimo estándar de 40 pies (dry van)."""
        return cls(
            name=name,
            category=LoadingSpaceCategory.CONTAINER,
            internal_dimensions=Dimensions3D(1203.0, 235.0, 239.0),
            door_position=DoorPosition.REAR,
            max_weight_kg=28750.0,
            notes=_PROFILE_NOTE,
        )

    @classmethod
    def standard_40ft_high_cube_container(
        cls, name: str = "Contenedor 40 pies High Cube (perfil estándar)"
    ) -> LoadingSpace:
        """Perfil orientativo de un contenedor marítimo de 40 pies High Cube."""
        return cls(
            name=name,
            category=LoadingSpaceCategory.CONTAINER,
            internal_dimensions=Dimensions3D(1203.0, 235.0, 269.0),
            door_position=DoorPosition.REAR,
            max_weight_kg=28560.0,
            notes=_PROFILE_NOTE,
        )
