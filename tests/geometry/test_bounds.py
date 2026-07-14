"""Pruebas de bounds (fits_inside_loading_space, validate_box_inside_loading_space)."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.bounds import (
    fits_inside_loading_space,
    validate_box_inside_loading_space,
)
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.exceptions import OutOfBoundsError

_SPACE = LoadingSpace(
    name="Espacio de prueba",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(100.0, 80.0, 60.0),
)


def _box(
    x: float, y: float, z: float, length: float, width: float, height: float
) -> AxisAlignedBox:
    return AxisAlignedBox(Position3D(x, y, z), Dimensions3D(length, width, height))


def test_fully_inside() -> None:
    box = _box(10.0, 10.0, 0.0, 20.0, 20.0, 20.0)
    assert fits_inside_loading_space(box, _SPACE)


def test_exactly_at_boundary() -> None:
    box = _box(0.0, 0.0, 0.0, 100.0, 80.0, 60.0)
    assert fits_inside_loading_space(box, _SPACE)


def test_out_of_bounds_x() -> None:
    box = _box(50.0, 0.0, 0.0, 60.0, 10.0, 10.0)
    assert not fits_inside_loading_space(box, _SPACE)


def test_out_of_bounds_y() -> None:
    box = _box(0.0, 70.0, 0.0, 10.0, 20.0, 10.0)
    assert not fits_inside_loading_space(box, _SPACE)


def test_out_of_bounds_z() -> None:
    box = _box(0.0, 0.0, 50.0, 10.0, 10.0, 20.0)
    assert not fits_inside_loading_space(box, _SPACE)


def test_negative_position_is_unreachable_by_construction() -> None:
    # Position3D (invariante de dominio, congelada) ya rechaza coordenadas
    # negativas antes de que una AxisAlignedBox pueda construirse, así que
    # fits_inside_loading_space nunca ve una posición negativa en la práctica.
    # El chequeo `min >= -GEOMETRY_EPSILON_CM` en fits_inside_loading_space se
    # mantiene de forma defensiva. Ver tests/domain/test_position.py para la
    # prueba real de ese rechazo.
    with pytest.raises(DomainValidationError):
        _box(-1.0, 0.0, 0.0, 10.0, 10.0, 10.0)


def test_within_tolerance_is_accepted() -> None:
    box = _box(0.0, 0.0, 0.0, 100.0 + 1e-12, 80.0, 60.0)
    assert fits_inside_loading_space(box, _SPACE)


def test_validate_raises_out_of_bounds_error() -> None:
    box = _box(50.0, 0.0, 0.0, 60.0, 10.0, 10.0)
    with pytest.raises(OutOfBoundsError):
        validate_box_inside_loading_space(box, _SPACE)


def test_validate_does_not_raise_when_fits() -> None:
    box = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    validate_box_inside_loading_space(box, _SPACE)
