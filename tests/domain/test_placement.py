"""Pruebas de Placement."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D

_BASE_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _make_placement(
    *, position: Position3D | None = None, orientation: Orientation | None = None, **overrides: int
) -> Placement:
    default_orientation = Orientation.from_base_dimensions(_BASE_DIMS, OrientationCode.LWH_XYZ)
    kwargs: dict[str, object] = {
        "load_unit_id": uuid4(),
        "instance_number": 1,
        "position": position or Position3D(10.0, 20.0, 0.0),
        "orientation": orientation or default_orientation,
        "sequence_number": 1,
    }
    kwargs.update(overrides)
    return Placement(**kwargs)  # type: ignore[arg-type]


def test_derived_properties() -> None:
    placement = _make_placement()
    assert placement.x_cm == 10.0
    assert placement.y_cm == 20.0
    assert placement.z_cm == 0.0
    assert placement.length_cm == 40.0
    assert placement.width_cm == 30.0
    assert placement.height_cm == 20.0


def test_max_bounds() -> None:
    placement = _make_placement()
    assert placement.max_x_cm == 50.0
    assert placement.max_y_cm == 50.0
    assert placement.max_z_cm == 20.0


def test_volume_cm3() -> None:
    placement = _make_placement()
    assert placement.volume_cm3 == _BASE_DIMS.volume_cm3


def test_invalid_instance_number_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        _make_placement(instance_number=0)


def test_invalid_sequence_number_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        _make_placement(sequence_number=0)
