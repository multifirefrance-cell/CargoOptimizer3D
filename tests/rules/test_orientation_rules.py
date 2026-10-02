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
    """Con las 6 declaradas explícitamente (no el valor por defecto reducido de la
    fase OPT-17), un producto normal no sufre ningún filtrado adicional."""
    unit = make_load_unit(
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        allowed_orientation_codes=tuple(OrientationCode),
    )
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
    unit = make_load_unit(
        dimensions=Dimensions3D(10.0, 10.0, 20.0),
        allowed_orientation_codes=tuple(OrientationCode),
    )
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


def test_individual_large_extinguisher_only_allows_horizontal_orientations() -> None:
    # Tres ejes distintos (60×15×20) para que ninguna orientación coincida
    # geométricamente → las 6 son únicas. Las 2 orientaciones verticales
    # (eje largo L=60 sobre Z: hwl_xyz y whl_xyz) se rechazan; las 4
    # horizontales (L sobre X o sobre Y) se mantienen.
    unit = make_individual_extinguisher(
        nominal_kg=5.0,
        dimensions=Dimensions3D(60.0, 15.0, 20.0),
        allowed_orientation_codes=tuple(OrientationCode),
    )
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 4
    # Ninguna orientación permitida tiene el eje largo (L=60) sobre Z.
    rejected_vertical = {OrientationCode.HWL_XYZ, OrientationCode.WHL_XYZ}
    assert all(o.code not in rejected_vertical for o in orientations)


def test_grouped_extinguisher_keeps_all_declared_orientations() -> None:
    unit = make_grouped_extinguisher(nominal_kg=2.0)
    orientations = allowed_orientations_for_load_unit(unit, DEFAULT_SPACE)
    assert len(orientations) == 6
