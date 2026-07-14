"""Pruebas de allowed_orientations_for_load_unit y evaluate_orientation."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.rules.codes import ORIENTATION_NOT_ALLOWED
from cargo_optimizer.rules.orientation_rules import (
    allowed_orientations_for_load_unit,
    evaluate_orientation,
)
from tests.rules._helpers import (
    DEFAULT_SPACE,
    make_grouped_extinguisher,
    make_individual_extinguisher,
    make_load_unit,
)


def test_normal_load_unit_returns_all_six_orientations() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0))
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 6


def test_declared_orientation_is_allowed() -> None:
    unit = make_load_unit(allowed_orientation_codes=(OrientationCode.LWH_XYZ,))
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.LWH_XYZ)
    result = evaluate_orientation(unit, DEFAULT_SPACE, orientation)
    assert result.is_allowed


def test_undeclared_orientation_is_rejected() -> None:
    unit = make_load_unit(allowed_orientation_codes=(OrientationCode.LWH_XYZ,))
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.WLH_XYZ)
    result = evaluate_orientation(unit, DEFAULT_SPACE, orientation)
    assert not result.is_allowed
    assert result.violations[0].code == ORIENTATION_NOT_ALLOWED


def test_repeated_dimensions_are_deduplicated() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(10.0, 10.0, 20.0))
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    seen_dims = {o.dimensions for o in orientations}
    assert len(orientations) == len(seen_dims)
    assert len(orientations) == 3


def test_order_is_deterministic() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0))
    first = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    second = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert first == second


def test_no_duplicates_even_with_cube() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(15.0, 15.0, 15.0))
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 1


def test_individual_large_extinguisher_only_allows_two_orientations() -> None:
    # Tres ejes distintos para que LWH_XYZ y LHW_XYZ no coincidan geométricamente.
    unit = make_individual_extinguisher(nominal_kg=5.0, dimensions=Dimensions3D(60.0, 15.0, 20.0))
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 2
    assert all(o.code in (OrientationCode.LWH_XYZ, OrientationCode.LHW_XYZ) for o in orientations)


def test_grouped_extinguisher_keeps_all_declared_orientations() -> None:
    unit = make_grouped_extinguisher(nominal_kg=2.0)
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 6
