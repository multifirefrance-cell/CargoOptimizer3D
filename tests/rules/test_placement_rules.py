"""Pruebas de evaluate_candidate_placement (evaluación compuesta)."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.codes import (
    COLLISION,
    EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD,
    OUT_OF_BOUNDS,
    UNSUPPORTED,
)
from cargo_optimizer.rules.placement_rules import evaluate_candidate_placement
from tests.rules._helpers import (
    make_context,
    make_grouped_extinguisher,
    make_load_unit,
    make_placement,
)

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def test_fully_valid_candidate() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    result = evaluate_candidate_placement(context)
    assert result.is_allowed
    assert result.violations == ()


def test_multiple_simultaneous_errors() -> None:
    # Fuera de límites en Z (flota) y, además, sin soporte -> ambas se reportan (no hay colisión).
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 5000.0))
    result = evaluate_candidate_placement(context)
    assert not result.is_allowed
    codes = {v.code for v in result.violations}
    assert OUT_OF_BOUNDS in codes
    assert UNSUPPORTED in codes


def test_grouped_extinguisher_capacity_warning_is_included() -> None:
    unit = make_grouped_extinguisher(nominal_kg=1.0, units_per_package=12)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    result = evaluate_candidate_placement(context)
    assert result.is_allowed
    assert any(v.code == EXTINGUISHER_GROUPED_CAPACITY_NONSTANDARD for v in result.violations)


def test_stable_violation_order() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 5000.0))
    result_a = evaluate_candidate_placement(context)
    result_b = evaluate_candidate_placement(context)
    assert [v.code for v in result_a.violations] == [v.code for v in result_b.violations]


def test_collision_does_not_cascade_into_support_errors() -> None:
    existing_unit = make_load_unit(sku="EXISTING", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS)
    # El candidato colisiona con `existing` (misma posición) y no está sobre el suelo
    # de una forma "normal" (coincide exactamente), así que sin la política de
    # no-cascada también aparecería UNSUPPORTED / MAX_STACK_EXCEEDED derivados de la
    # misma colisión.
    context = make_context(
        candidate_unit,
        position=Position3D(5.0, 5.0, 5.0),
        existing_placements=(existing,),
        load_units_by_id={candidate_unit.id: candidate_unit, existing_unit.id: existing_unit},
    )
    result = evaluate_candidate_placement(context)
    assert not result.is_allowed
    codes = [v.code for v in result.violations]
    assert COLLISION in codes
    assert UNSUPPORTED not in codes


def test_deterministic_result() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    result_a = evaluate_candidate_placement(context)
    result_b = evaluate_candidate_placement(context)
    assert result_a == result_b
