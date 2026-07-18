"""Equivalencia exacta entre usar el índice espacial y no usarlo (fase OPT-11).

`PlacementRuleContext.precomputed_spatial_index` es una optimización de
rendimiento pura (ver `docs/OptimizerPerformance.md` y
`geometry/spatial_index.py`): cuando el llamador la proporciona (siempre
`optimization`, en producción, vía `PackingState.spatial_index`),
restringe los recorridos de `existing_placements` a un superconjunto
barato de candidatos cercanos. Cuando no se proporciona (`None`, el
caso de toda prueba unitaria de `rules` que construye un
`PlacementRuleContext` a mano), el comportamiento es idéntico al de
antes de esta fase.

Estas pruebas demuestran, con layouts no triviales (colisión, soporte
parcial, apilamiento multi-nivel, peso soportado, y un caso límite de
cajas que se tocan justo en un borde de celda), que ambas rutas
producen exactamente el mismo `RuleEvaluation` — nunca una
aproximación, comparado byte a byte vía `==` sobre dataclasses
`frozen`. Ninguna prueba aquí compila un layout "fácil": cada una
existe para ejercitar un caso donde un índice espacial mal
implementado podría, en teoría, omitir un vecino relevante (falso
negativo) — ver también `tests/geometry/test_spatial_index.py` para la
prueba exhaustiva a nivel de `SpatialIndex` en sí.
"""

from __future__ import annotations

from dataclasses import replace

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.spatial_index import SpatialIndex
from cargo_optimizer.rules.placement_rules import evaluate_candidate_placement
from cargo_optimizer.rules.spatial_rules import evaluate_collision, evaluate_support
from cargo_optimizer.rules.stacking_rules import evaluate_stack_count
from tests.rules._helpers import make_context, make_load_unit, make_placement

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _with_index(context, cell_size_cm: float = 15.0):
    """Misma `context`, con un `SpatialIndex` real construido a partir de sus placements."""
    index = SpatialIndex(cell_size_cm=cell_size_cm)
    for placement, box in zip(context.existing_placements, context.existing_boxes, strict=True):
        index.insert(placement.sequence_number, box)
    return replace(context, precomputed_spatial_index=index)


def _three_level_stack_placements() -> tuple:
    base_unit = make_load_unit(sku="BASE", dimensions=_DIMS, weight_kg=10.0)
    mid_unit = make_load_unit(sku="MID", dimensions=_DIMS, weight_kg=8.0)
    base = make_placement(base_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    mid = make_placement(mid_unit, Position3D(0.0, 0.0, 20.0), sequence_number=2)
    top_unit = make_load_unit(sku="TOP", dimensions=_DIMS, weight_kg=6.0)
    top = make_placement(top_unit, Position3D(0.0, 0.0, 40.0), sequence_number=3)
    units_by_id = {base_unit.id: base_unit, mid_unit.id: mid_unit, top_unit.id: top_unit}
    return (base, mid, top), units_by_id


def test_evaluate_candidate_placement_identical_stack_scenario() -> None:
    existing_placements, units_by_id = _three_level_stack_placements()
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    units_by_id = {**units_by_id, candidate_unit.id: candidate_unit}
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 60.0),
        existing_placements=existing_placements,
        load_units_by_id=units_by_id,
    )
    assert evaluate_candidate_placement(context) == evaluate_candidate_placement(
        _with_index(context)
    )


def test_evaluate_stack_count_identical_stack_scenario() -> None:
    existing_placements, units_by_id = _three_level_stack_placements()
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    units_by_id = {**units_by_id, candidate_unit.id: candidate_unit}
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 60.0),
        existing_placements=existing_placements,
        load_units_by_id=units_by_id,
    )
    assert evaluate_stack_count(context) == evaluate_stack_count(_with_index(context))


def test_evaluate_collision_identical_when_candidate_overlaps() -> None:
    existing_unit = make_load_unit(sku="EXISTING", dimensions=_DIMS, weight_kg=10.0)
    existing = make_placement(existing_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    context = make_context(
        candidate_unit,
        position=Position3D(10.0, 10.0, 0.0),  # se solapa de verdad con `existing`
        existing_placements=(existing,),
        load_units_by_id={existing_unit.id: existing_unit, candidate_unit.id: candidate_unit},
    )
    result_without_index = evaluate_collision(context)
    result_with_index = evaluate_collision(_with_index(context))
    assert result_with_index == result_without_index
    assert not result_with_index.is_allowed


def test_evaluate_collision_identical_when_candidate_only_touches() -> None:
    """Tocarse (no solapar) nunca es colisión — debe seguir siendo así con índice."""
    existing_unit = make_load_unit(sku="EXISTING", dimensions=_DIMS, weight_kg=10.0)
    existing = make_placement(existing_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    context = make_context(
        candidate_unit,
        position=Position3D(40.0, 0.0, 0.0),  # toca a `existing` en x=40, no solapa
        existing_placements=(existing,),
        load_units_by_id={existing_unit.id: existing_unit, candidate_unit.id: candidate_unit},
    )
    result_without_index = evaluate_collision(context)
    result_with_index = evaluate_collision(_with_index(context))
    assert result_with_index == result_without_index
    assert result_with_index.is_allowed


def test_evaluate_support_identical_partial_support() -> None:
    """Dos cajas inferiores desalineadas: soporte parcial real, no solo total o nulo."""
    lower_a_unit = make_load_unit(sku="LOWER-A", dimensions=_DIMS, weight_kg=10.0)
    lower_b_unit = make_load_unit(sku="LOWER-B", dimensions=_DIMS, weight_kg=10.0)
    lower_a = make_placement(lower_a_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    lower_b = make_placement(lower_b_unit, Position3D(40.0, 0.0, 0.0), sequence_number=2)
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    # Candidata centrada sobre el límite entre ambas cajas inferiores: mitad
    # de su base sobre cada una, soporte total pero repartido entre dos
    # soportes directos distintos.
    context = make_context(
        candidate_unit,
        position=Position3D(20.0, 0.0, 20.0),
        existing_placements=(lower_a, lower_b),
        load_units_by_id={
            lower_a_unit.id: lower_a_unit,
            lower_b_unit.id: lower_b_unit,
            candidate_unit.id: candidate_unit,
        },
    )
    result_without_index = evaluate_support(context)
    result_with_index = evaluate_support(_with_index(context))
    assert result_with_index == result_without_index


def test_boundary_touching_at_cell_edge_finds_same_supporters_with_small_cells() -> None:
    """Caja de soporte justo en un borde de celda: el índice no debe perderla.

    `cell_size_cm=20.0` coincide exactamente con la altura de `_DIMS`
    (20 cm), así que el techo de la caja inferior cae justo sobre un
    límite de celda en Z — el caso que ejercita el margen de seguridad
    de `SpatialIndex` (ver `_BOUNDARY_PADDING_CM`).
    """
    lower_unit = make_load_unit(sku="LOWER", dimensions=_DIMS, weight_kg=10.0)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0), sequence_number=1)
    candidate_unit = make_load_unit(
        sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0, max_stack_count=2
    )
    context = make_context(
        candidate_unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={lower_unit.id: lower_unit, candidate_unit.id: candidate_unit},
    )
    result_without_index = evaluate_stack_count(context)
    result_with_index = evaluate_stack_count(_with_index(context, cell_size_cm=20.0))
    assert result_with_index == result_without_index
    assert result_with_index.is_allowed


def test_many_scattered_placements_same_decision_as_full_scan() -> None:
    """Layout más grande y disperso: compara la decisión completa, no solo un componente."""
    placements = []
    units_by_id = {}
    for i in range(30):
        unit = make_load_unit(sku=f"BOX-{i}", dimensions=_DIMS, weight_kg=8.0)
        units_by_id[unit.id] = unit
        row, col = divmod(i, 6)
        placements.append(
            make_placement(
                unit,
                Position3D(col * 40.0, row * 30.0, 0.0),
                sequence_number=i + 1,
            )
        )
    candidate_unit = make_load_unit(sku="CANDIDATE", dimensions=_DIMS, weight_kg=5.0)
    units_by_id[candidate_unit.id] = candidate_unit

    # Candidata sobre una esquina compartida por cuatro cajas de la rejilla.
    context = make_context(
        candidate_unit,
        position=Position3D(40.0, 30.0, 20.0),
        existing_placements=tuple(placements),
        load_units_by_id=units_by_id,
    )
    result_without_index = evaluate_candidate_placement(context)
    result_with_index = evaluate_candidate_placement(_with_index(context, cell_size_cm=25.0))
    assert result_with_index == result_without_index
