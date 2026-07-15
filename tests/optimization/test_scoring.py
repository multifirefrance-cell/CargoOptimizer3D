"""Pruebas de bounding volume y score_candidate."""

from __future__ import annotations

from cargo_optimizer.optimization.scoring import (
    bounding_dimensions,
    bounding_volume_cm3,
    bounding_volume_increment_cm3,
    local_residual_space_cm3,
    score_candidate,
)
from tests.optimization._helpers import DEFAULT_SPACE


def test_bounding_volume_empty_is_zero() -> None:
    assert bounding_volume_cm3(()) == 0.0
    assert bounding_dimensions(()) == (0.0, 0.0, 0.0)


def test_bounding_volume_increment_from_empty() -> None:
    increment = bounding_volume_increment_cm3((), 10.0, 10.0, 10.0)
    assert increment == 1000.0


def test_local_residual_space() -> None:
    residual = local_residual_space_cm3(DEFAULT_SPACE, 200.0, 100.0, 100.0)
    assert residual == 0.0
    residual_partial = local_residual_space_cm3(DEFAULT_SPACE, 100.0, 50.0, 50.0)
    assert residual_partial == 100.0 * 50.0 * 50.0


def test_score_prefers_lower_z() -> None:
    a = score_candidate(0.0, 5.0, 5.0, 1.0, 0.0, 0.0, 0, 0)
    b = score_candidate(10.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0, 1)
    assert a < b


def test_score_prefers_lower_x_when_z_ties() -> None:
    a = score_candidate(0.0, 0.0, 5.0, 1.0, 0.0, 0.0, 0, 0)
    b = score_candidate(0.0, 5.0, 0.0, 1.0, 0.0, 0.0, 0, 1)
    assert a < b


def test_score_prefers_lower_y_when_z_x_tie() -> None:
    a = score_candidate(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0, 0)
    b = score_candidate(0.0, 0.0, 5.0, 1.0, 0.0, 0.0, 0, 1)
    assert a < b


def test_score_prefers_higher_support_ratio() -> None:
    a = score_candidate(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0, 0)
    b = score_candidate(0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0, 1)
    assert a < b


def test_generation_index_is_final_tiebreak() -> None:
    a = score_candidate(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0, 0)
    b = score_candidate(0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0, 1)
    assert a < b


def test_repeatability() -> None:
    a1 = score_candidate(1.0, 2.0, 3.0, 0.8, 10.0, 5.0, 2, 7)
    a2 = score_candidate(1.0, 2.0, 3.0, 0.8, 10.0, 5.0, 2, 7)
    assert a1 == a2
