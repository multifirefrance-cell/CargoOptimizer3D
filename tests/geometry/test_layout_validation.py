"""Pruebas de validate_layout."""

from __future__ import annotations

from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.layout_validation import validate_layout

_SPACE = LoadingSpace(
    name="Camión de prueba",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
)
_DIMS = Dimensions3D(10.0, 10.0, 10.0)
_ORIENTATION = Orientation.from_base_dimensions(_DIMS, OrientationCode.LWH_XYZ)


def _placement(
    x: float,
    y: float,
    z: float,
    sequence_number: int,
    *,
    load_unit_id: object | None = None,
    instance_number: int = 1,
) -> Placement:
    return Placement(
        load_unit_id=load_unit_id or uuid4(),
        instance_number=instance_number,
        position=Position3D(x, y, z),
        orientation=_ORIENTATION,
        sequence_number=sequence_number,
    )


def test_empty_layout_is_valid() -> None:
    result = validate_layout(_SPACE, [])
    assert result.is_valid
    assert result.issues == ()


def test_single_valid_placement_on_ground() -> None:
    placement = _placement(0.0, 0.0, 0.0, 1)
    result = validate_layout(_SPACE, [placement])
    assert result.is_valid


def test_out_of_bounds_placement_is_detected() -> None:
    placement = _placement(95.0, 0.0, 0.0, 1)
    result = validate_layout(_SPACE, [placement])
    assert not result.is_valid
    assert any(issue.code == "OUT_OF_BOUNDS" for issue in result.issues)


def test_overlap_is_detected() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(5.0, 5.0, 0.0, 2)
    result = validate_layout(_SPACE, [p1, p2])
    assert not result.is_valid
    assert any(issue.code == "OVERLAP" for issue in result.issues)


def test_unsupported_placement_is_detected() -> None:
    placement = _placement(0.0, 0.0, 10.0, 1)  # Flota a 10 cm sin nada debajo.
    result = validate_layout(_SPACE, [placement])
    assert not result.is_valid
    assert any(issue.code == "UNSUPPORTED" for issue in result.issues)


def test_partial_support_allowed_when_full_support_not_required() -> None:
    lower = _placement(0.0, 0.0, 0.0, 1)
    upper = _placement(5.0, 0.0, 10.0, 2)  # Solo mitad de la base apoyada.
    result_strict = validate_layout(_SPACE, [lower, upper], require_full_support=True)
    result_lenient = validate_layout(_SPACE, [lower, upper], require_full_support=False)
    assert any(issue.code == "UNSUPPORTED" for issue in result_strict.issues)
    assert not any(issue.code == "UNSUPPORTED" for issue in result_lenient.issues)


def test_duplicate_sequence_number_is_detected() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(50.0, 0.0, 0.0, 1)
    result = validate_layout(_SPACE, [p1, p2])
    assert not result.is_valid
    assert any(issue.code == "DUPLICATE_SEQUENCE_NUMBER" for issue in result.issues)


def test_duplicate_instance_number_is_detected() -> None:
    shared_id = uuid4()
    p1 = _placement(0.0, 0.0, 0.0, 1, load_unit_id=shared_id, instance_number=1)
    p2 = _placement(50.0, 0.0, 0.0, 2, load_unit_id=shared_id, instance_number=1)
    result = validate_layout(_SPACE, [p1, p2])
    assert not result.is_valid
    assert any(issue.code == "DUPLICATE_INSTANCE_NUMBER" for issue in result.issues)


def test_different_instance_numbers_for_same_load_unit_are_valid() -> None:
    shared_id = uuid4()
    p1 = _placement(0.0, 0.0, 0.0, 1, load_unit_id=shared_id, instance_number=1)
    p2 = _placement(50.0, 0.0, 0.0, 2, load_unit_id=shared_id, instance_number=2)
    result = validate_layout(_SPACE, [p1, p2])
    assert result.is_valid


def test_multiple_issues_reported_together() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(95.0, 0.0, 0.0, 1)  # Fuera de límites y sequence_number duplicado.
    result = validate_layout(_SPACE, [p1, p2])
    codes = {issue.code for issue in result.issues}
    assert "OUT_OF_BOUNDS" in codes
    assert "DUPLICATE_SEQUENCE_NUMBER" in codes


def test_result_is_deterministic() -> None:
    p1 = _placement(0.0, 0.0, 0.0, 1)
    p2 = _placement(5.0, 5.0, 0.0, 2)
    result_a = validate_layout(_SPACE, [p1, p2])
    result_b = validate_layout(_SPACE, [p1, p2])
    assert result_a == result_b
