"""Pruebas de support (support_area_cm2, support_ratio, is_supported)."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.exceptions import GeometryValidationError
from cargo_optimizer.geometry.support import (
    horizontal_overlap_area_cm2,
    is_supported,
    support_ratio,
)


def _box(
    x: float, y: float, z: float, length: float, width: float, height: float
) -> AxisAlignedBox:
    return AxisAlignedBox(Position3D(x, y, z), Dimensions3D(length, width, height))


def test_box_on_ground_has_full_support() -> None:
    candidate = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, []) == 1.0
    assert is_supported(candidate, [])


def test_fully_supported_by_one_box_below() -> None:
    lower = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    candidate = _box(0.0, 0.0, 10.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower]) == pytest.approx(1.0)
    assert is_supported(candidate, [lower])


def test_partially_supported() -> None:
    lower = _box(0.0, 0.0, 0.0, 5.0, 10.0, 10.0)
    candidate = _box(0.0, 0.0, 10.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower]) == pytest.approx(0.5)
    assert not is_supported(candidate, [lower])
    assert is_supported(candidate, [lower], minimum_support_ratio=0.5)


def test_unsupported_box_floating_in_air() -> None:
    lower = _box(50.0, 50.0, 0.0, 5.0, 5.0, 5.0)
    candidate = _box(0.0, 0.0, 10.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower]) == 0.0
    assert not is_supported(candidate, [lower])


def test_supported_by_two_boxes() -> None:
    lower_a = _box(0.0, 0.0, 0.0, 5.0, 10.0, 10.0)
    lower_b = _box(5.0, 0.0, 0.0, 5.0, 10.0, 10.0)
    candidate = _box(0.0, 0.0, 10.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower_a, lower_b]) == pytest.approx(1.0)
    assert is_supported(candidate, [lower_a, lower_b])


def test_overlapping_support_areas_are_not_double_counted() -> None:
    # Ambas cajas inferiores cubren la misma región bajo el candidato: no debe superar 1.0.
    lower_a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    lower_b = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    candidate = _box(0.0, 0.0, 10.0, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower_a, lower_b]) == pytest.approx(1.0)


def test_invalid_minimum_support_ratio_is_rejected() -> None:
    candidate = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    with pytest.raises(GeometryValidationError):
        is_supported(candidate, [], minimum_support_ratio=1.5)
    with pytest.raises(GeometryValidationError):
        is_supported(candidate, [], minimum_support_ratio=-0.1)


def test_height_tolerance() -> None:
    lower = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # El candidato empieza 1e-12 cm por encima de la cara superior de `lower`: dentro de tolerancia.
    candidate = _box(0.0, 0.0, 10.0 + 1e-12, 10.0, 10.0, 10.0)
    assert support_ratio(candidate, [lower]) == pytest.approx(1.0)


def test_horizontal_overlap_area() -> None:
    lower = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    upper = _box(5.0, 5.0, 10.0, 10.0, 10.0, 10.0)
    assert horizontal_overlap_area_cm2(upper, lower) == pytest.approx(25.0)


def test_horizontal_overlap_area_zero_when_not_aligned() -> None:
    lower = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    upper = _box(50.0, 50.0, 10.0, 10.0, 10.0, 10.0)
    assert horizontal_overlap_area_cm2(upper, lower) == 0.0
