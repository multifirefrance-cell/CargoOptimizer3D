"""Pruebas de PackingResult."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult

_SPACE_WITH_WEIGHT_LIMIT = LoadingSpace(
    name="Camión",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),  # 1,000,000 cm3
    max_weight_kg=1000.0,
)

_SPACE_WITHOUT_WEIGHT_LIMIT = LoadingSpace(
    name="Bodega sin límite de peso",
    category=LoadingSpaceCategory.WAREHOUSE,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    max_weight_kg=None,
)


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "loading_space": _SPACE_WITH_WEIGHT_LIMIT,
        "placements": (),
        "unpacked_units": (),
        "requested_count": 10,
        "packed_count": 8,
        "used_volume_cm3": 500_000.0,
        "used_weight_kg": 400.0,
        "execution_time_seconds": 1.5,
        "algorithm_name": "test-algorithm",
    }
    kwargs.update(overrides)
    return kwargs


def test_utilization_percentages() -> None:
    result = PackingResult(**_base_kwargs())
    assert result.volume_utilization_percent == pytest.approx(50.0)
    assert result.weight_utilization_percent == pytest.approx(40.0)
    assert result.packing_completion_percent == pytest.approx(80.0)
    assert result.unpacked_count == 0


def test_space_without_weight_limit_yields_none_utilization() -> None:
    result = PackingResult(**_base_kwargs(loading_space=_SPACE_WITHOUT_WEIGHT_LIMIT))
    assert result.weight_utilization_percent is None


def test_packed_count_greater_than_requested_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        PackingResult(**_base_kwargs(requested_count=5, packed_count=10))


def test_negative_execution_time_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        PackingResult(**_base_kwargs(execution_time_seconds=-0.1))


def test_empty_result_is_valid_and_does_not_divide_by_zero() -> None:
    result = PackingResult(
        **_base_kwargs(
            requested_count=0,
            packed_count=0,
            used_volume_cm3=0.0,
            used_weight_kg=0.0,
        )
    )
    assert result.packing_completion_percent == 100.0
    assert result.volume_utilization_percent == 0.0
