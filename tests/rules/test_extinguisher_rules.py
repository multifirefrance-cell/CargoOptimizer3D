"""Pruebas del extintor individual >= 3 kg y de las cajas grupales de extintores."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.rules.codes import (
    EXTINGUISHER_AXIS_NOT_PARALLEL_TO_X,
    EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD,
    EXTINGUISHER_INDIVIDUAL_MUST_BE_HORIZONTAL,
)
from cargo_optimizer.rules.extinguisher_rules import (
    _LENGTH_AXIS_BY_CODE,
    evaluate_extinguisher_configuration,
    evaluate_extinguisher_orientation,
    is_grouped_small_extinguisher,
    is_individual_large_extinguisher,
    recommended_grouped_units_per_package,
)
from tests.rules._helpers import (
    DEFAULT_SPACE,
    make_grouped_extinguisher,
    make_individual_extinguisher,
    make_load_unit,
)


def _orientation(load_unit_dims, code: OrientationCode) -> Orientation:
    return Orientation.from_base_dimensions(load_unit_dims, code)


def test_length_axis_table_matches_actual_orientation_semantics() -> None:
    """Verifica que _LENGTH_AXIS_BY_CODE no haya divergido de Orientation.from_base_dimensions.

    Usa una caja "marcador" con las tres dimensiones distintas para que
    sea inequívoco qué eje recibe la dimensión `length_cm` original.
    """
    marker = Dimensions3D(3.0, 2.0, 1.0)  # length=3, width=2, height=1: todos distintos.
    for code, expected_axis in _LENGTH_AXIS_BY_CODE.items():
        rotated = Orientation.from_base_dimensions(marker, code)
        sizes = {"X": rotated.x_size_cm, "Y": rotated.y_size_cm, "Z": rotated.z_size_cm}
        actual_axis = next(axis for axis, size in sizes.items() if size == marker.length_cm)
        assert actual_axis == expected_axis, f"{code}: esperado {expected_axis}, real {actual_axis}"


# --- Extintor individual >= 3 kg -------------------------------------------------


def test_pqs_individual_3kg_is_large_extinguisher() -> None:
    unit = make_individual_extinguisher(nominal_kg=3.0, extinguisher_agent=ExtinguisherAgent.PQS)
    assert is_individual_large_extinguisher(unit)


def test_co2_individual_5kg_is_large_extinguisher() -> None:
    unit = make_individual_extinguisher(nominal_kg=5.0, extinguisher_agent=ExtinguisherAgent.CO2)
    assert is_individual_large_extinguisher(unit)


def test_horizontal_with_length_on_x_is_allowed() -> None:
    unit = make_individual_extinguisher(nominal_kg=3.0)
    for code in (OrientationCode.LWH_XYZ, OrientationCode.LHW_XYZ):
        orientation = _orientation(unit.dimensions, code)
        result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
        assert result.is_allowed, f"{code} debería estar permitido"


def test_vertical_is_forbidden() -> None:
    unit = make_individual_extinguisher(nominal_kg=3.0)
    for code in (OrientationCode.HWL_XYZ, OrientationCode.WHL_XYZ):
        orientation = _orientation(unit.dimensions, code)
        result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
        assert not result.is_allowed
        assert result.violations[0].code == EXTINGUISHER_INDIVIDUAL_MUST_BE_HORIZONTAL


def test_longitudinal_axis_on_y_is_forbidden() -> None:
    unit = make_individual_extinguisher(nominal_kg=3.0)
    for code in (OrientationCode.WLH_XYZ, OrientationCode.HLW_XYZ):
        orientation = _orientation(unit.dimensions, code)
        result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
        assert not result.is_allowed
        assert result.violations[0].code == EXTINGUISHER_AXIS_NOT_PARALLEL_TO_X


def test_longitudinal_axis_on_z_is_forbidden() -> None:
    # Mismo caso que "vertical prohibido": length termina en Z para HWL_XYZ y WHL_XYZ.
    unit = make_individual_extinguisher(nominal_kg=3.0)
    orientation = _orientation(unit.dimensions, OrientationCode.HWL_XYZ)
    result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
    assert not result.is_allowed


def test_rule_uses_nominal_weight_not_gross_weight() -> None:
    # weight_kg (peso bruto) es alto, pero extinguisher_nominal_kg (2 kg) no activa la regla.
    unit = make_individual_extinguisher(nominal_kg=2.0, weight_kg=50.0)
    assert not is_individual_large_extinguisher(unit)


def test_individual_2kg_does_not_trigger_rule() -> None:
    unit = make_individual_extinguisher(nominal_kg=2.0)
    assert not is_individual_large_extinguisher(unit)
    orientation = _orientation(unit.dimensions, OrientationCode.HWL_XYZ)
    result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
    assert result.is_allowed


def test_normal_product_10kg_does_not_trigger_rule() -> None:
    unit = make_load_unit(weight_kg=10.0)
    assert not is_individual_large_extinguisher(unit)
    orientation = _orientation(unit.dimensions, OrientationCode.HWL_XYZ)
    result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
    assert result.is_allowed


# --- Extintores grupales ----------------------------------------------------------


@pytest.mark.parametrize("nominal_kg", [1.0, 2.0, 3.0])
def test_grouped_boxes_can_go_vertical(nominal_kg: float) -> None:
    unit = make_grouped_extinguisher(nominal_kg=nominal_kg)
    assert is_grouped_small_extinguisher(unit)
    orientation = _orientation(unit.dimensions, OrientationCode.HWL_XYZ)
    result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
    assert result.is_allowed


def test_grouped_box_can_go_horizontal() -> None:
    unit = make_grouped_extinguisher(nominal_kg=1.0)
    orientation = _orientation(unit.dimensions, OrientationCode.LWH_XYZ)
    result = evaluate_extinguisher_orientation(unit, DEFAULT_SPACE, orientation)
    assert result.is_allowed


def test_grouped_box_respects_allowed_orientation_codes() -> None:
    unit = make_grouped_extinguisher(
        nominal_kg=1.0, allowed_orientation_codes=(OrientationCode.LWH_XYZ,)
    )
    assert unit.allowed_orientation_codes == (OrientationCode.LWH_XYZ,)


@pytest.mark.parametrize("max_stack_count", [1, 2, 5, 30])
def test_grouped_extinguisher_max_stack_count_is_preserved(max_stack_count: int) -> None:
    unit = make_grouped_extinguisher(nominal_kg=2.0, max_stack_count=max_stack_count)
    assert unit.max_stack_count == max_stack_count


@pytest.mark.parametrize("max_stack_count", [1, 2, 5, 30])
def test_individual_large_extinguisher_max_stack_count_is_preserved_not_overridden(
    max_stack_count: int,
) -> None:
    """Un extintor individual >= 3 kg ya no fuerza max_stack_count=1: se respeta el SKU."""
    unit = make_individual_extinguisher(nominal_kg=3.0, max_stack_count=max_stack_count)
    assert is_individual_large_extinguisher(unit)
    assert unit.max_stack_count == max_stack_count


@pytest.mark.parametrize(("nominal_kg", "expected"), [(1.0, 10), (2.0, 8), (3.0, 6)])
def test_recommended_capacities_have_no_warning_when_matched(
    nominal_kg: float, expected: int
) -> None:
    assert recommended_grouped_units_per_package(nominal_kg) == expected
    unit = make_grouped_extinguisher(nominal_kg=nominal_kg, units_per_package=expected)
    result = evaluate_extinguisher_configuration(unit)
    assert result.is_allowed
    assert not result.has_warnings


def test_different_capacity_generates_warning_not_error() -> None:
    unit = make_grouped_extinguisher(nominal_kg=1.0, units_per_package=12)
    result = evaluate_extinguisher_configuration(unit)
    assert result.is_allowed
    assert result.has_warnings
    assert result.warnings[0].code == EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD


def test_grouped_3kg_is_not_treated_as_large_individual() -> None:
    unit = make_grouped_extinguisher(nominal_kg=3.0)
    assert not is_individual_large_extinguisher(unit)
    assert is_grouped_small_extinguisher(unit)


def test_quantity_and_units_per_package_are_not_confused() -> None:
    unit = make_grouped_extinguisher(nominal_kg=1.0, units_per_package=10, quantity=5)
    assert unit.units_per_package == 10
    assert unit.quantity == 5
    assert unit.total_requested_units == 50
