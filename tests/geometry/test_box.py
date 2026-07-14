"""Pruebas de AxisAlignedBox."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement


def _box(
    x: float, y: float, z: float, length: float, width: float, height: float
) -> AxisAlignedBox:
    return AxisAlignedBox(Position3D(x, y, z), Dimensions3D(length, width, height))


def test_min_max_properties() -> None:
    box = _box(10.0, 20.0, 0.0, 40.0, 30.0, 20.0)
    assert box.min_x == 10.0
    assert box.min_y == 20.0
    assert box.min_z == 0.0
    assert box.max_x == 50.0
    assert box.max_y == 50.0
    assert box.max_z == 20.0


def test_volume_cm3() -> None:
    box = _box(0.0, 0.0, 0.0, 40.0, 30.0, 20.0)
    assert box.volume_cm3 == 24_000.0


def test_center() -> None:
    box = _box(0.0, 0.0, 0.0, 10.0, 20.0, 30.0)
    assert box.center_x == 5.0
    assert box.center_y == 10.0
    assert box.center_z == 15.0


def test_contains_point() -> None:
    box = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert box.contains_point(Position3D(5.0, 5.0, 5.0))
    assert box.contains_point(Position3D(0.0, 0.0, 0.0))
    assert box.contains_point(Position3D(10.0, 10.0, 10.0))
    assert not box.contains_point(Position3D(10.1, 5.0, 5.0))


def test_contains_box() -> None:
    outer = _box(0.0, 0.0, 0.0, 100.0, 100.0, 100.0)
    inner = _box(10.0, 10.0, 10.0, 5.0, 5.0, 5.0)
    assert outer.contains_box(inner)
    assert not inner.contains_box(outer)


def test_separated_boxes() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(20.0, 0.0, 0.0, 5.0, 5.0, 5.0)
    assert not a.intersects(b)
    assert not a.overlaps(b)
    assert not a.touches(b)
    assert a.intersection_volume_cm3(b) == 0.0


def test_overlapping_boxes() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(5.0, 5.0, 5.0, 10.0, 10.0, 10.0)
    assert a.intersects(b)
    assert a.overlaps(b)
    assert not a.touches(b)
    assert a.intersection_volume_cm3(b) == pytest.approx(125.0)


def test_face_contact_is_touching_not_overlapping() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(10.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert a.intersects(b)
    assert not a.overlaps(b)
    assert a.touches(b)
    assert a.intersection_volume_cm3(b) == 0.0


def test_edge_contact_is_touching_not_overlapping() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(10.0, 10.0, 0.0, 10.0, 10.0, 10.0)
    assert a.intersects(b)
    assert not a.overlaps(b)
    assert a.touches(b)


def test_vertex_contact_is_touching_not_overlapping() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(10.0, 10.0, 10.0, 10.0, 10.0, 10.0)
    assert a.intersects(b)
    assert not a.overlaps(b)
    assert a.touches(b)


def test_partial_intersection_volume() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(4.0, 3.0, 2.0, 10.0, 10.0, 10.0)
    # Solape: X in [4,10]=6, Y in [3,10]=7, Z in [2,10]=8 -> 6*7*8 = 336
    assert a.intersection_volume_cm3(b) == pytest.approx(336.0)


def test_symmetry() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    b = _box(5.0, 5.0, 5.0, 10.0, 10.0, 10.0)
    assert a.overlaps(b) == b.overlaps(a)
    assert a.intersects(b) == b.intersects(a)
    assert a.touches(b) == b.touches(a)
    assert a.intersection_volume_cm3(b) == b.intersection_volume_cm3(a)

    c = _box(10.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert a.touches(c) == c.touches(a)


def test_float_tolerance() -> None:
    a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # Un desplazamiento muchísimo menor que GEOMETRY_EPSILON_CM no debe cambiar el resultado.
    b = _box(10.0 + 1e-12, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert a.touches(b)
    assert not a.overlaps(b)


def test_box_from_placement_reuses_position_and_orientation_dimensions() -> None:
    base_dims = Dimensions3D(40.0, 30.0, 20.0)
    orientation = Orientation.from_base_dimensions(base_dims, OrientationCode.WLH_XYZ)
    placement = Placement(
        load_unit_id=uuid4(),
        instance_number=1,
        position=Position3D(1.0, 2.0, 3.0),
        orientation=orientation,
        sequence_number=1,
    )
    box = box_from_placement(placement)
    assert box.position == placement.position
    assert box.dimensions == orientation.dimensions
    assert box.min_x == 1.0
    assert box.max_x == 1.0 + orientation.x_size_cm
