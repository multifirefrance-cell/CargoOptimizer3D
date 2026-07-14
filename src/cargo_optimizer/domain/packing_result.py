"""PackingResult: resultado de una ejecución de optimización sobre un Loading Space.

Este módulo solo modela la estructura de datos y sus invariantes. La
lógica para construir un PackingResult a partir de un algoritmo de
optimización pertenece a la fase 4 (motor de optimización).
"""

from __future__ import annotations

from dataclasses import dataclass

from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit


@dataclass(frozen=True, slots=True)
class PackingResult:
    """Resultado completo de un intento de optimización de carga."""

    loading_space: LoadingSpace
    placements: tuple[Placement, ...]
    unpacked_units: tuple[UnpackedUnit, ...]
    requested_count: int
    packed_count: int
    used_volume_cm3: float
    used_weight_kg: float
    execution_time_seconds: float
    algorithm_name: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.requested_count < 0:
            raise DomainValidationError("requested_count no puede ser negativo.")
        if self.packed_count < 0:
            raise DomainValidationError("packed_count no puede ser negativo.")
        if self.packed_count > self.requested_count:
            raise DomainValidationError("packed_count no puede ser mayor que requested_count.")
        if self.execution_time_seconds < 0:
            raise DomainValidationError("execution_time_seconds no puede ser negativo.")
        if self.used_volume_cm3 < 0:
            raise DomainValidationError("used_volume_cm3 no puede ser negativo.")
        if self.used_weight_kg < 0:
            raise DomainValidationError("used_weight_kg no puede ser negativo.")
        if not self.algorithm_name.strip():
            raise DomainValidationError("algorithm_name no puede estar vacío.")

    @property
    def unpacked_count(self) -> int:
        return len(self.unpacked_units)

    @property
    def volume_utilization_percent(self) -> float:
        capacity = self.loading_space.capacity_volume_cm3
        if capacity <= 0:
            return 0.0
        return (self.used_volume_cm3 / capacity) * 100.0

    @property
    def weight_utilization_percent(self) -> float | None:
        """None cuando el Loading Space no declara un peso máximo (sin límite conocido)."""
        max_weight = self.loading_space.max_weight_kg
        if max_weight is None or max_weight <= 0:
            return None
        return (self.used_weight_kg / max_weight) * 100.0

    @property
    def packing_completion_percent(self) -> float:
        """100% cuando no se solicitó ninguna unidad (nada pendiente por definición)."""
        if self.requested_count == 0:
            return 100.0
        return (self.packed_count / self.requested_count) * 100.0
