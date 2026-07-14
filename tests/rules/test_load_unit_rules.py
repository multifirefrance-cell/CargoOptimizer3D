"""Pruebas de evaluate_load_unit_rules."""

from __future__ import annotations

from cargo_optimizer.rules.codes import EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD
from cargo_optimizer.rules.load_unit_rules import evaluate_load_unit_rules
from tests.rules._helpers import make_grouped_extinguisher, make_load_unit


def test_normal_load_unit_has_no_issues() -> None:
    unit = make_load_unit()
    result = evaluate_load_unit_rules(unit)
    assert result.is_allowed
    assert result.violations == ()


def test_grouped_extinguisher_with_nonstandard_capacity_warns() -> None:
    unit = make_grouped_extinguisher(nominal_kg=2.0, units_per_package=20)
    result = evaluate_load_unit_rules(unit)
    assert result.is_allowed
    assert result.violations[0].code == EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD
