"""Pruebas de collision (boxes_overlap, placement_overlaps_any, find_overlapping_placements)."""

from __future__ import annotations

from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.collision import (
    boxes_overlap,
    find_overlapping_placements,
    placement_overlaps_any,
)

_DIMS = Dimensions3D(10.0, 10.0, 10.0)
_ORIENTATION = Orientation.from_base_dimensions(_DIMS, OrientationCode.LWH_XYZ)


def _placement(x: float, y: float, z: float, sequence_number: int) -> Placement:
    return Placement(
        load_unit_id=uuid4(),
        instance_number=1,
        position=Position3D(x, y, z),
        orientation=_ORIENTATION,
        sequence_number=sequence_number,
    )


def _box(x: float, y: float, z: float) -> AxisAlignedBox:
    return AxisAlignedBox(Position3D(x, y, z), _DIMS)


def test_boxes_overlap_true_and_false() -> None:
    assert boxes_overlap(_box(0.0, 0.0, 0.0), _box(5.0, 5.0, 5.0))
    assert not boxes_overlap(_box(0.0, 0.0, 0.0), _box(20.0, 0.0, 0.0))


def test_touching_boxes_do_not_count_as_collision() -> None:
    assert not boxes_overlap(_box(0.0, 0.0, 0.0), _box(10.0, 0.0, 0.0))


def test_candidate_without_collision() -> None:
    existing = [_placement(0.0, 0.0, 0.0, 1)]
    candidate = _placement(20.0, 0.0, 0.0, 2)
    assert not placement_overlaps_any(candidate, existing)


def test_candidate_with_collision() -> None:
    existing = [_placement(0.0, 0.0, 0.0, 1)]
    candidate = _placement(5.0, 5.0, 5.0, 2)
    assert placement_overlaps_any(candidate, existing)


def test_multiple_placements_no_collision() -> None:
    placements = [
        _placement(0.0, 0.0, 0.0, 1),
        _placement(20.0, 0.0, 0.0, 2),
        _placement(40.0, 0.0, 0.0, 3),
    ]
    assert find_overlapping_placements(placements) == ()


def test_multiple_placements_with_collision_no_duplicates() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(5.0, 5.0, 5.0, 2)
    p3 = _placement(100.0, 0.0, 0.0, 3)
    pairs = find_overlapping_placements([p1, p2, p3])
    assert pairs == ((p1, p2),)


def test_no_self_comparison() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    pairs = find_overlapping_placements([p1])
    assert pairs == ()


def test_deterministic_order() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(5.0, 5.0, 5.0, 2)
    p3 = _placement(6.0, 6.0, 6.0, 3)
    result_a = find_overlapping_placements([p1, p2, p3])
    result_b = find_overlapping_placements([p1, p2, p3])
    assert result_a == result_b
    # Orden estable: (p1,p2), (p1,p3), (p2,p3) según i<j de la entrada.
    assert result_a == ((p1, p2), (p1, p3), (p2, p3))
