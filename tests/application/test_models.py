"""Pruebas de `MultiSpaceAssignmentRequest`/`Result`/`Progress`."""

from __future__ import annotations

import pytest

from cargo_optimizer.application.exceptions import MultiSpaceAssignmentValidationError
from cargo_optimizer.application.models import MultiSpaceAssignmentRequest
from tests.application._helpers import LARGE_SPACE, SMALL_SPACE, make_load_unit


def test_request_requires_at_least_one_candidate() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="loading_space_candidates"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(),
            load_units=(make_load_unit(),),
        )


def test_request_rejects_invalid_minimum_support_ratio() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="minimum_support_ratio"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(SMALL_SPACE,),
            load_units=(make_load_unit(),),
            minimum_support_ratio=1.5,
        )


def test_request_rejects_non_positive_time_limit() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="time_limit_seconds_per_space"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(SMALL_SPACE,),
            load_units=(make_load_unit(),),
            time_limit_seconds_per_space=0.0,
        )


def test_request_rejects_non_positive_max_iterations() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="max_iterations_per_space"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(SMALL_SPACE,),
            load_units=(make_load_unit(),),
            max_iterations_per_space=0,
        )


def test_request_rejects_non_positive_max_spaces() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="max_spaces"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(SMALL_SPACE,),
            load_units=(make_load_unit(),),
            max_spaces=0,
        )


def test_request_rejects_duplicate_skus() -> None:
    with pytest.raises(MultiSpaceAssignmentValidationError, match="SKU"):
        MultiSpaceAssignmentRequest(
            loading_space_candidates=(SMALL_SPACE,),
            load_units=(make_load_unit(sku="A"), make_load_unit(sku="A")),
        )


def test_request_allows_empty_load_units() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(),
    )
    assert request.load_units == ()


def test_build_space_request_applies_shared_parameters() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE, LARGE_SPACE),
        load_units=(make_load_unit(quantity=3),),
        minimum_support_ratio=0.8,
        time_limit_seconds_per_space=5.0,
        max_iterations_per_space=100,
        diagnostic_mode=True,
    )
    units = (make_load_unit(quantity=2),)
    space_request = request.build_space_request(LARGE_SPACE, units)

    assert space_request.loading_space is LARGE_SPACE
    assert space_request.load_units == units
    assert space_request.minimum_support_ratio == 0.8
    assert space_request.time_limit_seconds == 5.0
    assert space_request.max_iterations == 100
    assert space_request.diagnostic_mode is True
