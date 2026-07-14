"""Pruebas de apilamiento: count_stack_level, evaluate_stack_count, evaluate_supported_weight."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.rules.codes import MAX_STACK_EXCEEDED, SUPPORTED_WEIGHT_EXCEEDED
from cargo_optimizer.rules.stacking_rules import (
    count_stack_level,
    evaluate_stack_count,
    evaluate_supported_weight,
    find_direct_supporting_placements,
)
from tests.rules._helpers import (
    make_context,
    make_individual_extinguisher,
    make_load_unit,
    make_placement,
)

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def test_level_1_on_ground() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    placement = make_placement(unit, Position3D(0.0, 0.0, 0.0))
    box = box_from_placement(placement)
    assert count_stack_level(box, ()) == 1


def test_level_2_directly_above() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    upper_box = box_from_placement(upper)
    assert count_stack_level(upper_box, (lower,)) == 2


def test_limit_reached_is_allowed() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_stack_count=2)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, max_stack_count=2)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_stack_count(context).is_allowed


def test_limit_exceeded_is_rejected() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_stack_count=1)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, max_stack_count=1)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    result = evaluate_stack_count(context)
    assert not result.is_allowed
    assert result.violations[0].code == MAX_STACK_EXCEEDED


def test_individual_extinguisher_cannot_reach_level_2() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    extinguisher = make_individual_extinguisher(nominal_kg=3.0, dimensions=_DIMS, max_stack_count=5)
    context = make_context(
        extinguisher,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={extinguisher.id: extinguisher, lower_unit.id: lower_unit},
    )
    result = evaluate_stack_count(context)
    assert not result.is_allowed


def test_stack_with_different_skus() -> None:
    lower_unit = make_load_unit(sku="SKU-A", dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="SKU-B", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    upper_box = box_from_placement(upper)
    assert count_stack_level(upper_box, (lower,)) == 2


def test_multiple_support_uses_most_restrictive_level() -> None:
    tall_unit = make_load_unit(sku="TALL", dimensions=Dimensions3D(20.0, 30.0, 40.0))
    tall = make_placement(tall_unit, Position3D(0.0, 0.0, 0.0))
    short_lower_unit = make_load_unit(sku="SHORT-LOWER", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    short_lower = make_placement(short_lower_unit, Position3D(20.0, 0.0, 0.0), sequence_number=2)
    short_upper_unit = make_load_unit(sku="SHORT-UPPER", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    short_upper = make_placement(short_upper_unit, Position3D(20.0, 0.0, 20.0), sequence_number=3)
    # `candidate` se apoya en `tall` (nivel 1, altura 40) y en `short_upper` (nivel 2, altura 40).
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=Dimensions3D(40.0, 30.0, 10.0))
    candidate = make_placement(candidate_unit, Position3D(0.0, 0.0, 40.0), sequence_number=4)
    candidate_box = box_from_placement(candidate)
    level = count_stack_level(candidate_box, (tall, short_lower, short_upper))
    assert level == 3  # 1 + max(nivel(tall)=1, nivel(short_upper)=2)


def test_determinism() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    box = box_from_placement(upper)
    level_1 = count_stack_level(box, (lower,))
    level_2 = count_stack_level(box, (lower,))
    assert level_1 == level_2


# --- Peso soportado --------------------------------------------------------------


def test_supported_weight_without_limit() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=None)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=1000.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_supported_weight(context).is_allowed


def test_supported_weight_within_limit() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=50.0)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=30.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_supported_weight(context).is_allowed


def test_supported_weight_exactly_at_limit() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=30.0)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=30.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_supported_weight(context).is_allowed


def test_supported_weight_exceeded() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=10.0)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=30.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    result = evaluate_supported_weight(context)
    assert not result.is_allowed
    assert result.violations[0].code == SUPPORTED_WEIGHT_EXCEEDED


def test_supported_weight_accumulates_from_existing_load() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=25.0)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    already_stacked_unit = make_load_unit(sku="ALREADY", dimensions=_DIMS, weight_kg=20.0)
    already_stacked = make_placement(
        already_stacked_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2
    )
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=10.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 40.0),
        existing_placements=(lower, already_stacked),
        load_units_by_id={
            candidate_unit.id: candidate_unit,
            lower_unit.id: lower_unit,
            already_stacked_unit.id: already_stacked_unit,
        },
    )
    # lower ya soporta 20 kg (already_stacked) + 10 kg del candidato = 30 kg > 25 kg.
    result = evaluate_supported_weight(context)
    assert not result.is_allowed


def test_multiple_boxes_on_top() -> None:
    lower_unit = make_load_unit(
        dimensions=Dimensions3D(80.0, 30.0, 20.0), max_supported_weight_kg=100.0
    )
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(
        sku="CANDIDATE", dimensions=Dimensions3D(40.0, 30.0, 20.0), weight_kg=20.0
    )
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_supported_weight(context).is_allowed


def test_supported_weight_is_not_confused_with_max_stack_count() -> None:
    # max_stack_count alto no debe eximir del límite de peso soportado.
    lower_unit = make_load_unit(dimensions=_DIMS, max_supported_weight_kg=5.0, max_stack_count=10)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=50.0)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert not evaluate_supported_weight(context).is_allowed


def test_find_direct_supporting_placements() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    box = box_from_placement(upper)
    supporters = find_direct_supporting_placements(box, (lower,))
    assert supporters == (lower,)
