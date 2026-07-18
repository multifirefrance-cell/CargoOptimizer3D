"""Pruebas de la fachada RulesEngine."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.engine import RulesEngine
from tests.rules._helpers import DEFAULT_SPACE, make_context, make_load_unit

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def test_facade_delegates_allowed_orientations() -> None:
    engine = RulesEngine()
    unit = make_load_unit(dimensions=_DIMS, allowed_orientation_codes=tuple(OrientationCode))
    assert len(engine.allowed_orientations(unit, DEFAULT_SPACE)) == 6


def test_facade_delegates_evaluate_load_unit() -> None:
    engine = RulesEngine()
    unit = make_load_unit()
    result = engine.evaluate_load_unit(unit)
    assert result.is_allowed


def test_facade_delegates_evaluate_placement() -> None:
    engine = RulesEngine()
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    result = engine.evaluate_placement(context)
    assert result.is_allowed


def test_engine_has_no_mutable_state() -> None:
    engine = RulesEngine()
    assert not vars(engine)


def test_results_are_repeatable() -> None:
    engine = RulesEngine()
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    result_a = engine.evaluate_placement(context)
    result_b = engine.evaluate_placement(context)
    assert result_a == result_b
