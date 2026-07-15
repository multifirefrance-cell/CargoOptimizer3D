"""Pruebas de PackingRequest."""

from __future__ import annotations

import pytest

from cargo_optimizer.optimization.exceptions import PackingRequestValidationError
from cargo_optimizer.optimization.models import PackingRequest
from tests.optimization._helpers import DEFAULT_SPACE, make_load_unit


def test_valid_request() -> None:
    unit = make_load_unit()
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    assert request.load_units == (unit,)


def test_empty_load_units_is_valid() -> None:
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=())
    assert request.load_units == ()


def test_invalid_support_ratio() -> None:
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), minimum_support_ratio=1.5)
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), minimum_support_ratio=-0.1)


def test_invalid_time_limit() -> None:
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), time_limit_seconds=0.0)
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), time_limit_seconds=-5.0)


def test_invalid_max_iterations() -> None:
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), max_iterations=0)
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(), max_iterations=-1)


def test_duplicate_sku_is_rejected() -> None:
    unit_a = make_load_unit(sku="DUP")
    unit_b = make_load_unit(sku="DUP", name="Otra caja")
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit_a, unit_b))


def test_duplicate_id_is_rejected() -> None:
    unit_a = make_load_unit(sku="A")
    unit_b = make_load_unit(sku="B", id=unit_a.id)
    with pytest.raises(PackingRequestValidationError):
        PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit_a, unit_b))
