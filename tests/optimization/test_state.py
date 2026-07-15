"""Pruebas de `PackingState`, en particular la caché incremental de bounding box (fase 4.2)."""

from __future__ import annotations

from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.optimization.models import CandidatePlacement, PhysicalLoadInstance
from cargo_optimizer.optimization.state import PackingState
from cargo_optimizer.rules.results import RuleEvaluation
from tests.optimization._helpers import make_load_unit


def _candidate(position: Position3D, generation_index: int) -> CandidatePlacement:
    unit = make_load_unit()
    instance = PhysicalLoadInstance(load_unit=unit, instance_number=1, source_order=0)
    orientation = Orientation.from_base_dimensions(
        unit.dimensions, unit.allowed_orientation_codes[0]
    )
    placement = Placement(
        load_unit_id=unit.id,
        instance_number=1,
        position=position,
        orientation=orientation,
        sequence_number=generation_index + 1,
    )
    return CandidatePlacement(
        instance=instance,
        position=position,
        orientation=orientation,
        placement=placement,
        evaluation=RuleEvaluation.allowed(),
        score=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, generation_index),
        generation_index=generation_index,
    )


def test_bounding_dimensions_starts_at_zero() -> None:
    state = PackingState(load_units_by_id={})
    assert state.bounding_dimensions == (0.0, 0.0, 0.0)
    assert state.accepted_boxes == ()


def test_accept_placement_updates_bounding_dimensions_incrementally() -> None:
    state = PackingState(load_units_by_id={})
    candidate = _candidate(Position3D(0.0, 0.0, 0.0), 0)
    state.accept_placement(candidate)

    box = state.accepted_boxes[0]
    assert state.bounding_dimensions == (box.max_x, box.max_y, box.max_z)


def test_bounding_dimensions_tracks_the_maximum_across_placements() -> None:
    state = PackingState(load_units_by_id={})
    state.accept_placement(_candidate(Position3D(0.0, 0.0, 0.0), 0))
    state.accept_placement(_candidate(Position3D(40.0, 0.0, 0.0), 1))

    expected_max_x = max(box.max_x for box in state.accepted_boxes)
    expected_max_y = max(box.max_y for box in state.accepted_boxes)
    expected_max_z = max(box.max_z for box in state.accepted_boxes)
    assert state.bounding_dimensions == (expected_max_x, expected_max_y, expected_max_z)


def test_accepted_boxes_matches_placements_order() -> None:
    state = PackingState(load_units_by_id={})
    state.accept_placement(_candidate(Position3D(0.0, 0.0, 0.0), 0))
    state.accept_placement(_candidate(Position3D(40.0, 0.0, 0.0), 1))

    assert len(state.accepted_boxes) == len(state.placements)
    for placement, box in zip(state.placements, state.accepted_boxes, strict=True):
        assert box.min_x == placement.position.x_cm
