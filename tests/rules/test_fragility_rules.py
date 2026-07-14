"""Pruebas de evaluate_fragility."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.codes import FRAGILE_SUPPORT
from cargo_optimizer.rules.fragility_rules import evaluate_fragility
from tests.rules._helpers import make_context, make_load_unit, make_placement

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def test_candidate_over_normal_box() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, fragile=False)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    assert evaluate_fragility(context).is_allowed


def test_candidate_over_fragile_box_is_rejected() -> None:
    lower_unit = make_load_unit(dimensions=_DIMS, fragile=True)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={candidate_unit.id: candidate_unit, lower_unit.id: lower_unit},
    )
    result = evaluate_fragility(context)
    assert not result.is_allowed
    assert result.violations[0].code == FRAGILE_SUPPORT


def test_fragile_box_on_top_is_allowed() -> None:
    # La regla solo restringe qué se coloca ENCIMA de una frágil, no dónde se coloca ella misma.
    lower_unit = make_load_unit(dimensions=_DIMS, fragile=False)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    fragile_candidate = make_load_unit(sku="FRAGILE-CANDIDATE", dimensions=_DIMS, fragile=True)
    context = make_context(
        fragile_candidate,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={fragile_candidate.id: fragile_candidate, lower_unit.id: lower_unit},
    )
    assert evaluate_fragility(context).is_allowed


def test_partial_support_on_fragile_is_rejected() -> None:
    fragile_lower_unit = make_load_unit(
        sku="FRAGILE-LOWER", dimensions=Dimensions3D(20.0, 30.0, 20.0), fragile=True
    )
    fragile_lower = make_placement(fragile_lower_unit, Position3D(0.0, 0.0, 0.0))
    normal_lower_unit = make_load_unit(
        sku="NORMAL-LOWER", dimensions=Dimensions3D(20.0, 30.0, 20.0), fragile=False
    )
    normal_lower = make_placement(normal_lower_unit, Position3D(20.0, 0.0, 0.0), sequence_number=2)
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS)
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(fragile_lower, normal_lower),
        load_units_by_id={
            candidate_unit.id: candidate_unit,
            fragile_lower_unit.id: fragile_lower_unit,
            normal_lower_unit.id: normal_lower_unit,
        },
    )
    result = evaluate_fragility(context)
    assert not result.is_allowed
