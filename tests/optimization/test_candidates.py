"""Pruebas de build_candidate y orientation_fits_loading_space."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.optimization.candidates import build_candidate, orientation_fits_loading_space
from cargo_optimizer.optimization.models import PhysicalLoadInstance
from cargo_optimizer.rules.codes import UNSUPPORTED
from cargo_optimizer.rules.engine import RulesEngine
from tests.optimization._helpers import (
    DEFAULT_SPACE,
    make_grouped_extinguisher,
    make_load_unit,
)

_ENGINE = RulesEngine()


def _instance(unit: LoadUnit) -> PhysicalLoadInstance:
    return PhysicalLoadInstance(load_unit=unit, instance_number=1, source_order=0)


def test_orientation_fits_loading_space_rejects_oversized() -> None:
    huge = Orientation.from_base_dimensions(
        Dimensions3D(500.0, 500.0, 500.0), OrientationCode.LWH_XYZ
    )
    assert not orientation_fits_loading_space(huge, DEFAULT_SPACE)


def test_orientation_fits_loading_space_accepts_normal() -> None:
    small = Orientation.from_base_dimensions(
        Dimensions3D(40.0, 30.0, 20.0), OrientationCode.LWH_XYZ
    )
    assert orientation_fits_loading_space(small, DEFAULT_SPACE)


def test_unsupported_candidate_is_rejected() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0))
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.LWH_XYZ)
    floating_position = Position3D(0.0, 0.0, 50.0)  # sin nada debajo

    candidate = build_candidate(
        instance=_instance(unit),
        position=floating_position,
        orientation=orientation,
        orientation_order_index=0,
        loading_space=DEFAULT_SPACE,
        existing_placements=(),
        existing_boxes=(),
        load_units_by_id={unit.id: unit},
        rules_engine=_ENGINE,
        minimum_support_ratio=1.0,
        generation_index=0,
    )

    assert not candidate.evaluation.is_allowed
    assert any(v.code == UNSUPPORTED for v in candidate.evaluation.violations)


def test_grouped_extinguisher_can_use_vertical_orientation() -> None:
    unit = make_grouped_extinguisher(nominal_kg=2.0)
    vertical_orientation = Orientation.from_base_dimensions(
        unit.dimensions, OrientationCode.HWL_XYZ
    )
    candidate = build_candidate(
        instance=_instance(unit),
        position=Position3D(0.0, 0.0, 0.0),
        orientation=vertical_orientation,
        orientation_order_index=0,
        loading_space=DEFAULT_SPACE,
        existing_placements=(),
        existing_boxes=(),
        load_units_by_id={unit.id: unit},
        rules_engine=_ENGINE,
        minimum_support_ratio=1.0,
        generation_index=0,
    )
    assert candidate.evaluation.is_allowed
