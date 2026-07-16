"""Equivalencia exacta entre la ruta cacheada y la ruta de recálculo (fase OPT-02).

`PlacementRuleContext.precomputed_existing_boxes` es una optimización
de rendimiento pura (ver `docs/OptimizerPerformance.md`): cuando el
llamador la proporciona (siempre `optimization`, en producción), evita
reconstruir con `box_from_placement` cajas ya conocidas. Cuando no se
proporciona (`None`, el caso de la mayoría de pruebas unitarias de
`rules`), el comportamiento es idéntico al de antes de esta fase.

Estas pruebas demuestran, con un layout multi-nivel no trivial (varias
cajas apiladas con límites de peso soportado), que ambas rutas producen
exactamente el mismo `RuleEvaluation` — no una aproximación, el mismo
resultado, byte a byte comparable vía `==` sobre dataclasses `frozen`.
"""

from __future__ import annotations

from dataclasses import replace

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.rules.placement_rules import evaluate_candidate_placement
from cargo_optimizer.rules.stacking_rules import (
    evaluate_stack_count,
    evaluate_supported_weight,
)
from tests.rules._helpers import make_context, make_load_unit, make_placement

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _three_level_stack_placements() -> tuple:
    base_unit = make_load_unit(
        sku="BASE", dimensions=_DIMS, weight_kg=10.0, max_supported_weight_kg=50.0
    )
    mid_unit = make_load_unit(
        sku="MID", dimensions=_DIMS, weight_kg=8.0, max_supported_weight_kg=50.0
    )
    base = make_placement(base_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    mid = make_placement(mid_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    top_unit = make_load_unit(sku="TOP", dimensions=_DIMS, weight_kg=6.0)
    top = make_placement(top_unit, Position3D(0.0, 0.0, 40.0), sequence_number=3)
    units_by_id = {base_unit.id: base_unit, mid_unit.id: mid_unit, top_unit.id: top_unit}
    return (base, mid, top), units_by_id


def _make_contexts_with_and_without_cache(
    candidate_position: Position3D,
) -> tuple:
    existing_placements, units_by_id = _three_level_stack_placements()
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    units_by_id = {**units_by_id, candidate_unit.id: candidate_unit}

    context_without_cache = make_context(
        candidate_unit,
        position=candidate_position,
        existing_placements=existing_placements,
        load_units_by_id=units_by_id,
    )
    precomputed_boxes = tuple(box_from_placement(p) for p in existing_placements)
    context_with_cache = replace(
        context_without_cache, precomputed_existing_boxes=precomputed_boxes
    )
    return context_with_cache, context_without_cache


def test_evaluate_candidate_placement_identical_with_and_without_box_cache() -> None:
    context_with_cache, context_without_cache = _make_contexts_with_and_without_cache(
        Position3D(0.0, 0.0, 60.0)
    )
    assert evaluate_candidate_placement(context_with_cache) == evaluate_candidate_placement(
        context_without_cache
    )


def test_evaluate_stack_count_identical_with_and_without_box_cache() -> None:
    context_with_cache, context_without_cache = _make_contexts_with_and_without_cache(
        Position3D(0.0, 0.0, 60.0)
    )
    assert evaluate_stack_count(context_with_cache) == evaluate_stack_count(context_without_cache)


def test_evaluate_supported_weight_identical_with_and_without_box_cache() -> None:
    # Peso deliberadamente alto para forzar una violación real y comparar
    # también el contenido de las violaciones, no solo `is_allowed`.
    existing_placements, units_by_id = _three_level_stack_placements()
    heavy_unit = make_load_unit(sku="HEAVY", dimensions=_DIMS, weight_kg=100.0)
    units_by_id = {**units_by_id, heavy_unit.id: heavy_unit}

    context_without_cache = make_context(
        heavy_unit,
        position=Position3D(0.0, 0.0, 60.0),
        existing_placements=existing_placements,
        load_units_by_id=units_by_id,
    )
    precomputed_boxes = tuple(box_from_placement(p) for p in existing_placements)
    context_with_cache = replace(
        context_without_cache, precomputed_existing_boxes=precomputed_boxes
    )

    result_with_cache = evaluate_supported_weight(context_with_cache)
    result_without_cache = evaluate_supported_weight(context_without_cache)

    assert result_with_cache == result_without_cache
    assert not result_with_cache.is_allowed
