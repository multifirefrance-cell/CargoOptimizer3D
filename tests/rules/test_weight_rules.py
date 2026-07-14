"""Pruebas de current_loaded_weight_kg y evaluate_loading_space_weight."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.codes import LOADING_SPACE_WEIGHT_EXCEEDED
from cargo_optimizer.rules.weight_rules import (
    current_loaded_weight_kg,
    evaluate_loading_space_weight,
)
from tests.rules._helpers import make_context, make_load_unit, make_placement

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _space(max_weight_kg: float | None) -> LoadingSpace:
    return LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(1000.0, 200.0, 200.0),
        max_weight_kg=max_weight_kg,
    )


def test_without_limit() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=1000.0)
    context = make_context(unit, loading_space=_space(None), position=Position3D(0.0, 0.0, 0.0))
    assert evaluate_loading_space_weight(context).is_allowed


def test_within_limit() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=50.0)
    context = make_context(unit, loading_space=_space(100.0), position=Position3D(0.0, 0.0, 0.0))
    assert evaluate_loading_space_weight(context).is_allowed


def test_exactly_at_limit() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=100.0)
    context = make_context(unit, loading_space=_space(100.0), position=Position3D(0.0, 0.0, 0.0))
    assert evaluate_loading_space_weight(context).is_allowed


def test_exceeded() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=150.0)
    context = make_context(unit, loading_space=_space(100.0), position=Position3D(0.0, 0.0, 0.0))
    result = evaluate_loading_space_weight(context)
    assert not result.is_allowed
    assert result.violations[0].code == LOADING_SPACE_WEIGHT_EXCEEDED


def test_several_existing_instances_accumulate() -> None:
    existing_unit = make_load_unit(sku="EXISTING", dimensions=_DIMS, weight_kg=30.0)
    existing_1 = make_placement(existing_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    existing_2 = make_placement(
        existing_unit, Position3D(50.0, 0.0, 0.0), sequence_number=2, instance_number=2
    )
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=30.0)
    context = make_context(
        candidate_unit,
        loading_space=_space(80.0),
        position=Position3D(100.0, 0.0, 0.0),
        existing_placements=(existing_1, existing_2),
        load_units_by_id={candidate_unit.id: candidate_unit, existing_unit.id: existing_unit},
    )
    # 30 + 30 (existentes) + 30 (candidato) = 90 > 80.
    result = evaluate_loading_space_weight(context)
    assert not result.is_allowed


def test_unknown_references_do_not_crash_and_contribute_zero() -> None:
    existing_unit = make_load_unit(sku="EXISTING", dimensions=_DIMS, weight_kg=30.0)
    existing = make_placement(existing_unit, Position3D(0.0, 0.0, 0.0))
    total = current_loaded_weight_kg((existing,), {})
    assert total == 0.0


def test_candidate_weight_is_included() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=99.0)
    context = make_context(unit, loading_space=_space(100.0), position=Position3D(0.0, 0.0, 0.0))
    assert evaluate_loading_space_weight(context).is_allowed
    unit_over = make_load_unit(dimensions=_DIMS, weight_kg=101.0)
    context_over = make_context(
        unit_over, loading_space=_space(100.0), position=Position3D(0.0, 0.0, 0.0)
    )
    assert not evaluate_loading_space_weight(context_over).is_allowed
