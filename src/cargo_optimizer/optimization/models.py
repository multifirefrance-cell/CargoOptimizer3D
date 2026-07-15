"""Tipos de datos inmutables del motor de optimización.

`PackingState` (mutable) vive en `state.py`, no aquí: este módulo es
exclusivamente de datos inmutables (`@dataclass(frozen=True, slots=True)`,
mismo estilo que `domain`, ver ADR-0005).
"""

from __future__ import annotations

from dataclasses import dataclass

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.optimization.exceptions import PackingRequestValidationError
from cargo_optimizer.rules.results import RuleEvaluation


@dataclass(frozen=True, slots=True)
class PackingRequest:
    """Una solicitud de optimización completa e inmutable."""

    loading_space: LoadingSpace
    load_units: tuple[LoadUnit, ...]
    minimum_support_ratio: float = 1.0
    time_limit_seconds: float | None = None
    max_iterations: int | None = None
    diagnostic_mode: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.minimum_support_ratio <= 1.0:
            raise PackingRequestValidationError("minimum_support_ratio debe estar entre 0 y 1.")
        if self.time_limit_seconds is not None and self.time_limit_seconds <= 0:
            raise PackingRequestValidationError(
                "time_limit_seconds debe ser mayor que 0 cuando se especifica."
            )
        if self.max_iterations is not None and self.max_iterations <= 0:
            raise PackingRequestValidationError(
                "max_iterations debe ser mayor que 0 cuando se especifica."
            )
        skus = [unit.sku for unit in self.load_units]
        if len(skus) != len(set(skus)):
            raise PackingRequestValidationError("Los SKU de load_units deben ser únicos.")
        unit_ids = [unit.id for unit in self.load_units]
        if len(unit_ids) != len(set(unit_ids)):
            raise PackingRequestValidationError("Los id de load_units deben ser únicos.")


@dataclass(frozen=True, slots=True)
class PhysicalLoadInstance:
    """Un paquete físico concreto a colocar.

    No confundir con `LoadUnit` (la especificación de un tipo de
    paquete y cuántos se piden): hay `load_unit.quantity` instancias
    de estas por cada `LoadUnit`. `units_per_package` nunca se
    expande: una caja grupal con 10 extintores sigue siendo una única
    `PhysicalLoadInstance`.
    """

    load_unit: LoadUnit
    instance_number: int
    source_order: int


@dataclass(frozen=True, slots=True)
class PackingProgress:
    """Instantánea inmutable de avance para un callback de progreso opcional."""

    processed_instances: int
    total_instances: int
    packed_count: int
    unpacked_count: int
    elapsed_seconds: float
    current_sku: str | None = None


@dataclass(frozen=True, slots=True)
class CandidatePlacement:
    """Un candidato de colocación ya evaluado. Interno de `optimization`.

    `placement` usa un `sequence_number` provisional (el índice de
    generación del candidato dentro de la búsqueda de esta instancia,
    nunca el definitivo): solo sirve para satisfacer la invariante de
    `Placement`, que exige un entero positivo. El `Placement`
    realmente aceptado se reconstruye con el número de secuencia
    correcto en `PackingState.accept_placement`; el de aquí se
    descarta si el candidato no resulta elegido o no es válido.
    """

    instance: PhysicalLoadInstance
    position: Position3D
    orientation: Orientation
    placement: Placement
    evaluation: RuleEvaluation
    score: tuple[float, ...]
    generation_index: int
