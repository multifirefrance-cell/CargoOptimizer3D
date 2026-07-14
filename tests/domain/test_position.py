"""Pruebas de Position3D."""

from __future__ import annotations

import math

import pytest

from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.position import Position3D


def test_valid_position() -> None:
    p = Position3D(10.0, 20.0, 30.0)
    assert p.as_tuple() == (10.0, 20.0, 30.0)


def test_zero_is_valid() -> None:
    Position3D(0.0, 0.0, 0.0)


@pytest.mark.parametrize("bad_value", [-0.01, -100.0])
def test_negative_is_rejected(bad_value: float) -> None:
    with pytest.raises(DomainValidationError):
        Position3D(bad_value, 0.0, 0.0)


def test_nan_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        Position3D(math.nan, 0.0, 0.0)


def test_infinity_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        Position3D(math.inf, 0.0, 0.0)
