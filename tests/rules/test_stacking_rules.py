"""Pruebas de apilamiento: find_direct_supporting_placements, stack_level_of,
compute_stack_levels, evaluate_stack_count.

No hay peso soportado ni propagación de peso entre cajas (eliminado por
completo, fase OPT-13): este módulo solo controla el número máximo de
niveles permitido por SKU.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import DEFAULT_MAX_STACK_COUNT
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.rules.codes import MAX_STACK_EXCEEDED
from cargo_optimizer.rules.stacking_rules import (
    compute_stack_levels,
    evaluate_stack_count,
    find_direct_supporting_placements,
    stack_level_of,
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
    assert stack_level_of(box, (), {}) == 1


def test_level_2_directly_above() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    upper_box = box_from_placement(upper)
    levels = compute_stack_levels((lower, upper))
    supporters = find_direct_supporting_placements(upper_box, (lower,))
    assert stack_level_of(upper_box, supporters, levels) == 2


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


def test_specific_limit_of_five_is_respected() -> None:
    """Un límite concreto (ni "no apilable" ni "sin límite") se respeta exactamente."""
    unit = make_load_unit(dimensions=_DIMS, max_stack_count=5)
    placements: list = []
    for level in range(4):
        placements.append(
            make_placement(unit, Position3D(0.0, 0.0, level * 20.0), sequence_number=level + 1)
        )
    # Nivel 5 (encima de 4 ya colocados): dentro del límite.
    context_allowed = make_context(
        unit,
        position=Position3D(0.0, 0.0, 80.0),
        existing_placements=tuple(placements),
        load_units_by_id={unit.id: unit},
    )
    assert evaluate_stack_count(context_allowed).is_allowed

    # Nivel 6: fuera del límite de 5.
    placements.append(make_placement(unit, Position3D(0.0, 0.0, 80.0), sequence_number=5))
    context_rejected = make_context(
        unit,
        position=Position3D(0.0, 0.0, 100.0),
        existing_placements=tuple(placements),
        load_units_by_id={unit.id: unit},
    )
    result = evaluate_stack_count(context_rejected)
    assert not result.is_allowed
    assert result.violations[0].code == MAX_STACK_EXCEEDED


def test_high_stack_count_allows_many_levels() -> None:
    """`DEFAULT_MAX_STACK_COUNT` (30, ver `LoadUnit`) permite más niveles que un límite bajo."""
    unit = make_load_unit(dimensions=_DIMS, max_stack_count=DEFAULT_MAX_STACK_COUNT)
    placements = tuple(
        make_placement(unit, Position3D(0.0, 0.0, level * 20.0), sequence_number=level + 1)
        for level in range(10)
    )
    # Nivel 11: muy por encima de lo que permitiría max_stack_count=1 o un
    # límite bajo cualquiera, pero muy por debajo del límite configurado de 30.
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 200.0),
        existing_placements=placements,
        load_units_by_id={unit.id: unit},
    )
    assert evaluate_stack_count(context).is_allowed


def test_individual_extinguisher_with_limit_one_cannot_reach_level_2() -> None:
    """Con max_stack_count=1 configurado explícitamente, un extintor individual no apila."""
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    extinguisher = make_individual_extinguisher(nominal_kg=3.0, dimensions=_DIMS, max_stack_count=1)
    context = make_context(
        extinguisher,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={extinguisher.id: extinguisher, lower_unit.id: lower_unit},
    )
    result = evaluate_stack_count(context)
    assert not result.is_allowed
    assert result.violations[0].code == MAX_STACK_EXCEEDED


def test_individual_extinguisher_with_limit_five_can_reach_level_2() -> None:
    """Sin la excepción automática eliminada: un extintor individual >= 3 kg con
    max_stack_count=5 apila exactamente como cualquier otro LoadUnit con ese límite."""
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
    assert result.is_allowed


def test_stack_with_different_skus() -> None:
    lower_unit = make_load_unit(sku="SKU-A", dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="SKU-B", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    upper_box = box_from_placement(upper)
    levels = compute_stack_levels((lower, upper))
    supporters = find_direct_supporting_placements(upper_box, (lower,))
    assert stack_level_of(upper_box, supporters, levels) == 2


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
    existing = (tall, short_lower, short_upper)
    levels = compute_stack_levels(existing)
    supporters = find_direct_supporting_placements(candidate_box, existing)
    level = stack_level_of(candidate_box, supporters, levels)
    assert level == 3  # 1 + max(nivel(tall)=1, nivel(short_upper)=2)


def test_determinism() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    box = box_from_placement(upper)
    levels_1 = compute_stack_levels((lower, upper))
    levels_2 = compute_stack_levels((lower, upper))
    assert levels_1 == levels_2
    supporters = find_direct_supporting_placements(box, (lower,))
    assert stack_level_of(box, supporters, levels_1) == stack_level_of(box, supporters, levels_2)


def test_compute_stack_levels_processes_bottom_up_without_recursion() -> None:
    """Tres niveles: `compute_stack_levels` calcula todo en una sola pasada."""
    base_unit = make_load_unit(sku="BASE", dimensions=_DIMS)
    base = make_placement(base_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    mid_unit = make_load_unit(sku="MID", dimensions=_DIMS)
    mid = make_placement(mid_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    top_unit = make_load_unit(sku="TOP", dimensions=_DIMS)
    top = make_placement(top_unit, Position3D(0.0, 0.0, 40.0), sequence_number=3)
    levels = compute_stack_levels((base, mid, top))
    assert levels == {1: 1, 2: 2, 3: 3}


def test_find_direct_supporting_placements() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    upper_unit = make_load_unit(sku="UPPER", dimensions=_DIMS)
    upper = make_placement(upper_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    box = box_from_placement(upper)
    supporters = find_direct_supporting_placements(box, (lower,))
    assert supporters == (lower,)
