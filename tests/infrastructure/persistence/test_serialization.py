"""Pruebas de las funciones puras de traducción domain <-> dict de `serialization.py`."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.infrastructure.persistence import serialization as ser


def test_dimensions_round_trip() -> None:
    value = Dimensions3D(40.0, 30.0, 20.0)
    assert ser.dimensions_from_dict(ser.dimensions_to_dict(value)) == value


def test_position_round_trip() -> None:
    value = Position3D(1.0, 2.0, 3.0)
    assert ser.position_from_dict(ser.position_to_dict(value)) == value


def test_orientation_round_trip() -> None:
    value = Orientation.from_base_dimensions(
        Dimensions3D(40.0, 30.0, 20.0), OrientationCode.WLH_XYZ
    )
    restored = ser.orientation_from_dict(ser.orientation_to_dict(value))
    assert restored == value


def test_placement_round_trip() -> None:
    orientation = Orientation.from_base_dimensions(
        Dimensions3D(40.0, 30.0, 20.0), OrientationCode.LWH_XYZ
    )
    value = Placement(
        load_unit_id=LoadUnit(sku="X", name="X", dimensions=Dimensions3D(1, 1, 1), weight_kg=1).id,
        instance_number=2,
        position=Position3D(0.0, 0.0, 0.0),
        orientation=orientation,
        sequence_number=5,
    )
    assert ser.placement_from_dict(ser.placement_to_dict(value)) == value


def test_unpacked_unit_round_trip() -> None:
    value = UnpackedUnit(
        load_unit_id=LoadUnit(sku="X", name="X", dimensions=Dimensions3D(1, 1, 1), weight_kg=1).id,
        instance_number=1,
        reason_code="OUT_OF_SPACE",
        reason_message="No cupo.",
    )
    assert ser.unpacked_unit_from_dict(ser.unpacked_unit_to_dict(value)) == value


def test_loading_space_round_trip_with_weight_limit() -> None:
    value = LoadingSpace(
        name="Camión",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(600.0, 240.0, 240.0),
        door_position=DoorPosition.REAR,
        max_weight_kg=8000.0,
        notes="Notas",
    )
    assert ser.loading_space_from_dict(ser.loading_space_to_dict(value)) == value


def test_loading_space_round_trip_without_weight_limit() -> None:
    value = LoadingSpace(
        name="Bodega",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(2000.0, 1500.0, 500.0),
        door_position=DoorPosition.UNRESTRICTED,
        max_weight_kg=None,
    )
    assert ser.loading_space_from_dict(ser.loading_space_to_dict(value)) == value


def test_load_unit_round_trip_including_extinguisher_fields() -> None:
    from cargo_optimizer.domain.enums import ExtinguisherAgent

    value = LoadUnit(
        sku="EXT-1",
        name="Extintor PQS",
        dimensions=Dimensions3D(60.0, 20.0, 20.0),
        weight_kg=6.0,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.PQS,
        extinguisher_nominal_kg=5.0,
    )
    assert ser.load_unit_from_dict(ser.load_unit_to_dict(value)) == value


def test_load_unit_round_trip_non_extinguisher() -> None:
    value = LoadUnit(
        sku="BOX-1",
        name="Caja",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=10.0,
        quantity=4,
        max_supported_weight_kg=50.0,
        fragile=True,
        notes="Frágil",
    )
    assert ser.load_unit_from_dict(ser.load_unit_to_dict(value)) == value
