"""Fábricas compartidas para los tests de `cargo_optimizer.rules`."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID, uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.context import PlacementRuleContext

DEFAULT_SPACE = LoadingSpace(
    name="Camión de pruebas",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(1000.0, 200.0, 200.0),
)
_ORIGIN = Position3D(0.0, 0.0, 0.0)


def make_load_unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-001",
        "name": "Caja normal",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def make_individual_extinguisher(nominal_kg: float = 3.0, **overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "EXT-IND",
        "name": "Extintor individual",
        "dimensions": Dimensions3D(60.0, 20.0, 20.0),
        "weight_kg": 4.0,
        "package_type": PackageType.INDIVIDUAL,
        "is_extinguisher": True,
        "extinguisher_agent": ExtinguisherAgent.PQS,
        "extinguisher_nominal_kg": nominal_kg,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def make_grouped_extinguisher(nominal_kg: float = 1.0, **overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "EXT-GRP",
        "name": "Extintores en caja grupal",
        "dimensions": Dimensions3D(50.0, 40.0, 30.0),
        "weight_kg": 12.0,
        "package_type": PackageType.GROUPED_BOX,
        "units_per_package": 10,
        "is_extinguisher": True,
        "extinguisher_agent": ExtinguisherAgent.PQS,
        "extinguisher_nominal_kg": nominal_kg,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def make_orientation(
    dimensions: Dimensions3D, code: OrientationCode = OrientationCode.LWH_XYZ
) -> Orientation:
    return Orientation.from_base_dimensions(dimensions, code)


def make_placement(
    load_unit: LoadUnit,
    position: Position3D,
    *,
    orientation: Orientation | None = None,
    sequence_number: int = 1,
    instance_number: int = 1,
) -> Placement:
    return Placement(
        load_unit_id=load_unit.id,
        instance_number=instance_number,
        position=position,
        orientation=orientation or make_orientation(load_unit.dimensions),
        sequence_number=sequence_number,
    )


def make_context(
    load_unit: LoadUnit,
    *,
    loading_space: LoadingSpace = DEFAULT_SPACE,
    position: Position3D = _ORIGIN,
    orientation: Orientation | None = None,
    existing_placements: tuple[Placement, ...] = (),
    load_units_by_id: Mapping[UUID, LoadUnit] | None = None,
) -> PlacementRuleContext:
    if load_units_by_id is not None:
        units_by_id = dict(load_units_by_id)
    else:
        units_by_id = {load_unit.id: load_unit}
    return PlacementRuleContext(
        loading_space=loading_space,
        load_unit=load_unit,
        candidate_position=position,
        candidate_orientation=orientation or make_orientation(load_unit.dimensions),
        existing_placements=existing_placements,
        load_units_by_id=units_by_id,
    )


def unique_id() -> UUID:
    return uuid4()
