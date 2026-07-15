"""Construcción de PackingResult a partir del estado final de una ejecución."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit

ALGORITHM_NAME = "greedy_extreme_point_v1"


def build_packing_result(
    loading_space: LoadingSpace,
    placements: tuple[Placement, ...],
    unpacked_units: tuple[UnpackedUnit, ...],
    requested_count: int,
    load_units_by_id: Mapping[UUID, LoadUnit],
    execution_time_seconds: float,
    warnings: tuple[str, ...],
) -> PackingResult:
    """Construye el `PackingResult` final.

    `requested_count` es el número de instancias geométricas (paquetes
    físicos), nunca `total_requested_units` (que cuenta también los
    ítems internos de una caja grupal, p. ej. extintores). El peso
    usado suma `weight_kg` (peso bruto del paquete) por cada placement
    colocado, nunca `extinguisher_nominal_kg`. Los porcentajes de
    utilización no se recalculan aquí: ya son propiedades de
    `PackingResult` (fase 2.1); esta función solo aporta los campos
    crudos que esas propiedades necesitan.
    """
    used_volume_cm3 = sum(p.volume_cm3 for p in placements)
    used_weight_kg = 0.0
    for placement in placements:
        unit = load_units_by_id.get(placement.load_unit_id)
        if unit is not None:
            used_weight_kg += unit.weight_kg

    return PackingResult(
        loading_space=loading_space,
        placements=placements,
        unpacked_units=unpacked_units,
        requested_count=requested_count,
        packed_count=len(placements),
        used_volume_cm3=used_volume_cm3,
        used_weight_kg=used_weight_kg,
        execution_time_seconds=execution_time_seconds,
        algorithm_name=ALGORITHM_NAME,
        warnings=warnings,
    )
