"""Pruebas de generate_candidate_positions."""

from __future__ import annotations

from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.candidate_points import generate_candidate_positions

_DIMS = Dimensions3D(10.0, 20.0, 5.0)
_ORIENTATION = Orientation.from_base_dimensions(_DIMS, OrientationCode.LWH_XYZ)


def _placement(x: float, y: float, z: float, sequence_number: int) -> Placement:
    return Placement(
        load_unit_id=uuid4(),
        instance_number=1,
        position=Position3D(x, y, z),
        orientation=_ORIENTATION,
        sequence_number=sequence_number,
    )


def test_no_placements_returns_only_origin() -> None:
    assert generate_candidate_positions([]) == (Position3D(0.0, 0.0, 0.0),)


def test_single_placement_generates_expected_points() -> None:
    placement = _placement(0.0, 0.0, 0.0, 1)
    positions = generate_candidate_positions([placement])
    expected = {
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (0.0, 20.0, 0.0),
        (0.0, 0.0, 5.0),
    }
    assert {p.as_tuple() for p in positions} == expected


def test_several_placements() -> None:
    placements = [_placement(0.0, 0.0, 0.0, 1), _placement(10.0, 0.0, 0.0, 2)]
    positions = generate_candidate_positions(placements)
    # Origen + 3 puntos por placement = hasta 7, sin duplicados exactos aquí.
    assert len(positions) == 7


def test_deduplication_with_tolerance() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(0.0, 0.0, 0.0, 2)  # Mismo placement (misma caja) que p1.
    positions = generate_candidate_positions([p1, p2])
    positions_only_p1 = generate_candidate_positions([p1])
    assert positions == positions_only_p1


def test_order_is_sorted_by_z_then_x_then_y() -> None:
    placement = _placement(0.0, 0.0, 0.0, 1)
    positions = generate_candidate_positions([placement])
    keys = [(p.z_cm, p.x_cm, p.y_cm) for p in positions]
    assert keys == sorted(keys)


def test_determinism() -> None:
    placements = [
        _placement(0.0, 0.0, 0.0, 1),
        _placement(10.0, 0.0, 0.0, 2),
        _placement(0.0, 20.0, 0.0, 3),
    ]
    first = generate_candidate_positions(placements)
    second = generate_candidate_positions(placements)
    assert first == second
