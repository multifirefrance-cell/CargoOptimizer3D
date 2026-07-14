"""Pruebas de Dimensions3D."""

from __future__ import annotations

import math

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.exceptions import DomainValidationError


def test_valid_dimensions() -> None:
    d = Dimensions3D(100.0, 50.0, 30.0)
    assert d.as_tuple() == (100.0, 50.0, 30.0)


@pytest.mark.parametrize("bad_value", [0.0, -1.0])
def test_zero_and_negative_are_rejected(bad_value: float) -> None:
    with pytest.raises(DomainValidationError):
        Dimensions3D(bad_value, 10.0, 10.0)


def test_nan_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        Dimensions3D(math.nan, 10.0, 10.0)


def test_infinity_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        Dimensions3D(math.inf, 10.0, 10.0)


def test_bool_is_rejected_even_though_bool_is_int_subtype() -> None:
    with pytest.raises(DomainValidationError):
        Dimensions3D(True, 10.0, 10.0)  # type: ignore[arg-type]


def test_volume_cm3() -> None:
    d = Dimensions3D(100.0, 50.0, 30.0)
    assert d.volume_cm3 == 150_000.0


def test_volume_m3() -> None:
    d = Dimensions3D(100.0, 50.0, 30.0)
    assert d.volume_m3 == pytest.approx(0.15)


def test_all_orientations_returns_six_for_distinct_dimensions() -> None:
    d = Dimensions3D(100.0, 50.0, 30.0)
    orientations = d.all_orientations()
    assert len(orientations) == 6
    assert len(set(orientations)) == 6


def test_all_orientations_deduplicates_when_dimensions_equal() -> None:
    cube = Dimensions3D(10.0, 10.0, 10.0)
    assert cube.all_orientations() == (cube,)

    two_equal = Dimensions3D(10.0, 10.0, 20.0)
    orientations = two_equal.all_orientations()
    assert len(orientations) == 3
    assert len(set(orientations)) == 3


def test_all_orientations_order_is_deterministic() -> None:
    d = Dimensions3D(100.0, 50.0, 30.0)
    first_call = d.all_orientations()
    second_call = d.all_orientations()
    assert first_call == second_call


def test_equality() -> None:
    assert Dimensions3D(100.0, 50.0, 30.0) == Dimensions3D(100.0, 50.0, 30.0)
    assert Dimensions3D(100.0, 50.0, 30.0) != Dimensions3D(100.0, 50.0, 31.0)
