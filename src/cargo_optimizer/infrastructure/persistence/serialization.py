"""Conversión explícita entre entidades de `domain` y diccionarios JSON-seguros.

Cada función traduce un único tipo, campo por campo — nunca
`__dict__`, `pickle` ni una biblioteca de serialización automática
(ver `docs/ProjectFiles.md`). La validación de los valores reconstruidos
la hacen los propios constructores de `domain` (`__post_init__`): estas
funciones no reimplementan ninguna regla de negocio, solo empaquetan y
desempaquetan datos. `project_file_repository.py` es responsable de
convertir cualquier excepción de aquí (`KeyError`, `TypeError`,
`ValueError`, `DomainValidationError`, `DuplicateSkuError`) en el error
tipado de persistencia correspondiente.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    DoorPosition,
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.project import CargoProject
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit

JSONDict = dict[str, Any]


def dimensions_to_dict(value: Dimensions3D) -> JSONDict:
    return {
        "length_cm": value.length_cm,
        "width_cm": value.width_cm,
        "height_cm": value.height_cm,
    }


def dimensions_from_dict(data: JSONDict) -> Dimensions3D:
    return Dimensions3D(
        length_cm=float(data["length_cm"]),
        width_cm=float(data["width_cm"]),
        height_cm=float(data["height_cm"]),
    )


def position_to_dict(value: Position3D) -> JSONDict:
    return {"x_cm": value.x_cm, "y_cm": value.y_cm, "z_cm": value.z_cm}


def position_from_dict(data: JSONDict) -> Position3D:
    return Position3D(
        x_cm=float(data["x_cm"]),
        y_cm=float(data["y_cm"]),
        z_cm=float(data["z_cm"]),
    )


def orientation_to_dict(value: Orientation) -> JSONDict:
    return {"code": value.code.value, "dimensions": dimensions_to_dict(value.dimensions)}


def orientation_from_dict(data: JSONDict) -> Orientation:
    return Orientation(
        code=OrientationCode(data["code"]),
        dimensions=dimensions_from_dict(data["dimensions"]),
    )


def placement_to_dict(value: Placement) -> JSONDict:
    return {
        "load_unit_id": str(value.load_unit_id),
        "instance_number": value.instance_number,
        "position": position_to_dict(value.position),
        "orientation": orientation_to_dict(value.orientation),
        "sequence_number": value.sequence_number,
    }


def placement_from_dict(data: JSONDict) -> Placement:
    return Placement(
        load_unit_id=UUID(data["load_unit_id"]),
        instance_number=int(data["instance_number"]),
        position=position_from_dict(data["position"]),
        orientation=orientation_from_dict(data["orientation"]),
        sequence_number=int(data["sequence_number"]),
    )


def unpacked_unit_to_dict(value: UnpackedUnit) -> JSONDict:
    return {
        "load_unit_id": str(value.load_unit_id),
        "instance_number": value.instance_number,
        "reason_code": value.reason_code,
        "reason_message": value.reason_message,
    }


def unpacked_unit_from_dict(data: JSONDict) -> UnpackedUnit:
    return UnpackedUnit(
        load_unit_id=UUID(data["load_unit_id"]),
        instance_number=int(data["instance_number"]),
        reason_code=str(data["reason_code"]),
        reason_message=str(data["reason_message"]),
    )


def loading_space_to_dict(value: LoadingSpace) -> JSONDict:
    return {
        "id": str(value.id),
        "name": value.name,
        "category": value.category.value,
        "internal_dimensions": dimensions_to_dict(value.internal_dimensions),
        "door_position": value.door_position.value,
        "max_weight_kg": value.max_weight_kg,
        "notes": value.notes,
    }


def loading_space_from_dict(data: JSONDict) -> LoadingSpace:
    max_weight = data["max_weight_kg"]
    return LoadingSpace(
        id=UUID(data["id"]),
        name=str(data["name"]),
        category=LoadingSpaceCategory(data["category"]),
        internal_dimensions=dimensions_from_dict(data["internal_dimensions"]),
        door_position=DoorPosition(data["door_position"]),
        max_weight_kg=None if max_weight is None else float(max_weight),
        notes=str(data["notes"]),
    )


def load_unit_to_dict(value: LoadUnit) -> JSONDict:
    return {
        "id": str(value.id),
        "sku": value.sku,
        "name": value.name,
        "dimensions": dimensions_to_dict(value.dimensions),
        "weight_kg": value.weight_kg,
        "quantity": value.quantity,
        "package_type": value.package_type.value,
        "units_per_package": value.units_per_package,
        "max_stack_count": value.max_stack_count,
        "max_supported_weight_kg": value.max_supported_weight_kg,
        "allowed_orientation_codes": [code.value for code in value.allowed_orientation_codes],
        "fragile": value.fragile,
        "is_extinguisher": value.is_extinguisher,
        "extinguisher_agent": value.extinguisher_agent.value,
        "extinguisher_nominal_kg": value.extinguisher_nominal_kg,
        "color_hex": value.color_hex,
        "notes": value.notes,
    }


def load_unit_from_dict(data: JSONDict) -> LoadUnit:
    max_supported = data["max_supported_weight_kg"]
    extinguisher_nominal = data["extinguisher_nominal_kg"]
    return LoadUnit(
        id=UUID(data["id"]),
        sku=str(data["sku"]),
        name=str(data["name"]),
        dimensions=dimensions_from_dict(data["dimensions"]),
        weight_kg=float(data["weight_kg"]),
        quantity=int(data["quantity"]),
        package_type=PackageType(data["package_type"]),
        units_per_package=int(data["units_per_package"]),
        max_stack_count=int(data["max_stack_count"]),
        max_supported_weight_kg=None if max_supported is None else float(max_supported),
        allowed_orientation_codes=tuple(
            OrientationCode(code) for code in data["allowed_orientation_codes"]
        ),
        fragile=bool(data["fragile"]),
        is_extinguisher=bool(data["is_extinguisher"]),
        extinguisher_agent=ExtinguisherAgent(data["extinguisher_agent"]),
        extinguisher_nominal_kg=(
            None if extinguisher_nominal is None else float(extinguisher_nominal)
        ),
        color_hex=str(data["color_hex"]),
        notes=str(data["notes"]),
    )


def packing_result_to_dict(value: PackingResult) -> JSONDict:
    return {
        "loading_space": loading_space_to_dict(value.loading_space),
        "placements": [placement_to_dict(p) for p in value.placements],
        "unpacked_units": [unpacked_unit_to_dict(u) for u in value.unpacked_units],
        "requested_count": value.requested_count,
        "packed_count": value.packed_count,
        "used_volume_cm3": value.used_volume_cm3,
        "used_weight_kg": value.used_weight_kg,
        "execution_time_seconds": value.execution_time_seconds,
        "algorithm_name": value.algorithm_name,
        "warnings": list(value.warnings),
    }


def packing_result_from_dict(data: JSONDict) -> PackingResult:
    return PackingResult(
        loading_space=loading_space_from_dict(data["loading_space"]),
        placements=tuple(placement_from_dict(p) for p in data["placements"]),
        unpacked_units=tuple(unpacked_unit_from_dict(u) for u in data["unpacked_units"]),
        requested_count=int(data["requested_count"]),
        packed_count=int(data["packed_count"]),
        used_volume_cm3=float(data["used_volume_cm3"]),
        used_weight_kg=float(data["used_weight_kg"]),
        execution_time_seconds=float(data["execution_time_seconds"]),
        algorithm_name=str(data["algorithm_name"]),
        warnings=tuple(str(w) for w in data["warnings"]),
    )


def cargo_project_to_dict(value: CargoProject) -> JSONDict:
    return {
        "id": str(value.id),
        "name": value.name,
        "notes": value.notes,
        "schema_version": value.schema_version,
        "loading_space": loading_space_to_dict(value.loading_space),
        "load_units": [load_unit_to_dict(u) for u in value.load_units],
        "latest_result": (
            None if value.latest_result is None else packing_result_to_dict(value.latest_result)
        ),
    }


def cargo_project_from_dict(data: JSONDict) -> CargoProject:
    latest_result = data["latest_result"]
    return CargoProject(
        id=UUID(data["id"]),
        name=str(data["name"]),
        notes=str(data["notes"]),
        schema_version=str(data["schema_version"]),
        loading_space=loading_space_from_dict(data["loading_space"]),
        load_units=tuple(load_unit_from_dict(u) for u in data["load_units"]),
        latest_result=None if latest_result is None else packing_result_from_dict(latest_result),
    )
