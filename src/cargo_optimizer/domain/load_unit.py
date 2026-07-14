"""LoadUnit: entidad que representa cualquier unidad de carga.

Universal por diseño (ver ADR-0002): una caja, un pallet, un tambor o
un extintor son todos LoadUnit, nunca "producto".

Distinción importante entre tres cantidades que se confunden con
facilidad (ver docs/DomainModel.md para el detalle):

- ``quantity``: número de paquetes físicos solicitados.
- ``units_per_package``: unidades individuales dentro de cada paquete
  (relevante para ``grouped_box``, p. ej. una caja con 12 unidades).
- ``total_requested_units`` = ``quantity`` * ``units_per_package``.

La regla especial de horizontalidad de extintores (no apilar de canto)
no se implementa aquí: pertenece al motor de restricciones (fase 3).
Este modelo solo deja los campos (`is_extinguisher`,
`extinguisher_agent`, `extinguisher_nominal_kg`) listos para que esa
fase pueda apoyarse en ellos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.orientation import Orientation

_COLOR_HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
_ALL_ORIENTATION_CODES: tuple[OrientationCode, ...] = tuple(OrientationCode)


def _dedupe_preserving_order(codes: tuple[OrientationCode, ...]) -> tuple[OrientationCode, ...]:
    seen: set[OrientationCode] = set()
    ordered: list[OrientationCode] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class LoadUnit:
    """Una unidad de carga: caja, pallet, tambor, cilindro, maquinaria, extintor, etc."""

    sku: str
    name: str
    dimensions: Dimensions3D
    weight_kg: float
    quantity: int = 1
    package_type: PackageType = PackageType.INDIVIDUAL
    units_per_package: int = 1
    max_stack_count: int = 1
    max_supported_weight_kg: float | None = None
    allowed_orientation_codes: tuple[OrientationCode, ...] = _ALL_ORIENTATION_CODES
    fragile: bool = False
    is_extinguisher: bool = False
    extinguisher_agent: ExtinguisherAgent = ExtinguisherAgent.NOT_APPLICABLE
    extinguisher_nominal_kg: float | None = None
    color_hex: str = "#CCCCCC"
    notes: str = ""
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.sku.strip():
            raise DomainValidationError("El SKU del Load Unit no puede estar vacío.")
        if not self.name.strip():
            raise DomainValidationError("El nombre del Load Unit no puede estar vacío.")
        if self.weight_kg < 0:
            raise DomainValidationError("weight_kg no puede ser negativo.")
        if self.quantity < 1:
            raise DomainValidationError("quantity debe ser mayor o igual que 1.")
        if self.units_per_package < 1:
            raise DomainValidationError("units_per_package debe ser mayor o igual que 1.")
        if self.max_stack_count < 1:
            raise DomainValidationError("max_stack_count debe ser mayor o igual que 1.")
        if self.max_supported_weight_kg is not None and self.max_supported_weight_kg < 0:
            raise DomainValidationError("max_supported_weight_kg no puede ser negativo.")
        if not self.allowed_orientation_codes:
            raise DomainValidationError("allowed_orientation_codes no puede estar vacío.")
        if not _COLOR_HEX_PATTERN.match(self.color_hex):
            raise DomainValidationError("color_hex debe tener el formato '#RRGGBB'.")
        if self.package_type is PackageType.INDIVIDUAL and self.units_per_package != 1:
            raise DomainValidationError(
                "Un package_type 'individual' debe tener units_per_package = 1."
            )
        self._validate_extinguisher_fields()

        object.__setattr__(
            self,
            "allowed_orientation_codes",
            _dedupe_preserving_order(self.allowed_orientation_codes),
        )

    def _validate_extinguisher_fields(self) -> None:
        if self.is_extinguisher:
            if self.extinguisher_agent is ExtinguisherAgent.NOT_APPLICABLE:
                raise DomainValidationError(
                    "Un Load Unit marcado como extintor debe declarar un extinguisher_agent válido."
                )
            if self.extinguisher_nominal_kg is None or self.extinguisher_nominal_kg <= 0:
                raise DomainValidationError(
                    "Un Load Unit marcado como extintor debe declarar extinguisher_nominal_kg > 0."
                )
        else:
            if self.extinguisher_agent is not ExtinguisherAgent.NOT_APPLICABLE:
                raise DomainValidationError(
                    "Un Load Unit que no es extintor debe tener "
                    "extinguisher_agent = not_applicable."
                )
            if self.extinguisher_nominal_kg is not None:
                raise DomainValidationError(
                    "Un Load Unit que no es extintor no debe declarar extinguisher_nominal_kg."
                )

    @property
    def package_volume_cm3(self) -> float:
        return self.dimensions.volume_cm3

    @property
    def total_requested_packages(self) -> int:
        return self.quantity

    @property
    def total_requested_units(self) -> int:
        return self.quantity * self.units_per_package

    @property
    def total_requested_weight_kg(self) -> float:
        return self.weight_kg * self.quantity

    def candidate_orientations(self) -> tuple[Orientation, ...]:
        """Las orientaciones concretas resultantes de aplicar cada código permitido."""
        return tuple(
            Orientation.from_base_dimensions(self.dimensions, code)
            for code in self.allowed_orientation_codes
        )
