"""Pruebas de Rectangle2D y union_area_cm2."""

from __future__ import annotations

import pytest

from cargo_optimizer.geometry.rectangles import Rectangle2D, union_area_cm2


def test_empty_list_has_zero_area() -> None:
    assert union_area_cm2([]) == 0.0


def test_single_rectangle() -> None:
    r = Rectangle2D(0.0, 0.0, 10.0, 5.0)
    assert union_area_cm2([r]) == pytest.approx(50.0)


def test_separated_rectangles_sum_areas() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(20.0, 0.0, 30.0, 10.0)
    assert union_area_cm2([a, b]) == pytest.approx(200.0)


def test_overlapping_rectangles_do_not_double_count() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(5.0, 5.0, 15.0, 15.0)
    # Área individual: 100 + 100 = 200; solape: 5x5=25. Unión = 175.
    assert union_area_cm2([a, b]) == pytest.approx(175.0)


def test_contained_rectangle() -> None:
    outer = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    inner = Rectangle2D(2.0, 2.0, 5.0, 5.0)
    assert union_area_cm2([outer, inner]) == pytest.approx(outer.area_cm2)


def test_complex_intersections_of_three_rectangles() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(5.0, 0.0, 15.0, 10.0)
    c = Rectangle2D(8.0, 0.0, 20.0, 10.0)
    # Unión total en X: [0, 20] con altura 10 -> 200 (todas cubren el mismo rango Y completo).
    assert union_area_cm2([a, b, c]) == pytest.approx(200.0)


def test_order_independence() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(5.0, 5.0, 15.0, 15.0)
    c = Rectangle2D(3.0, 3.0, 8.0, 8.0)
    area_1 = union_area_cm2([a, b, c])
    area_2 = union_area_cm2([c, b, a])
    area_3 = union_area_cm2([b, a, c])
    assert area_1 == pytest.approx(area_2)
    assert area_1 == pytest.approx(area_3)


def test_intersection_of_overlapping_rectangles() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(5.0, 5.0, 15.0, 15.0)
    intersection = a.intersection(b)
    assert intersection is not None
    assert intersection.area_cm2 == pytest.approx(25.0)


def test_intersection_of_separated_rectangles_is_none() -> None:
    a = Rectangle2D(0.0, 0.0, 10.0, 10.0)
    b = Rectangle2D(20.0, 0.0, 30.0, 10.0)
    assert a.intersection(b) is None


def test_invalid_rectangle_is_rejected() -> None:
    from cargo_optimizer.geometry.exceptions import GeometryValidationError

    with pytest.raises(GeometryValidationError):
        Rectangle2D(10.0, 0.0, 0.0, 10.0)
