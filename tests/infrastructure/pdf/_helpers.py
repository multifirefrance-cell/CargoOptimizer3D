"""Constructores de `PackingResult` de ejemplo para las pruebas de `infrastructure/pdf/`."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit


def make_full_result() -> tuple[PackingResult, dict]:
    """Un `PackingResult` con productos cargados, no cargados y avisos."""
    space = LoadingSpace(
        name="Contenedor 20'",
        category=LoadingSpaceCategory.CONTAINER,
        internal_dimensions=Dimensions3D(590, 235, 239),
        max_weight_kg=28000.0,
    )
    box = LoadUnit(
        sku="SKU-1",
        name="Caja de prueba",
        dimensions=Dimensions3D(50, 40, 30),
        weight_kg=10.0,
        quantity=2,
    )
    orientation = Orientation.from_base_dimensions(box.dimensions, OrientationCode.LWH_XYZ)
    placements = (
        Placement(
            load_unit_id=box.id,
            instance_number=1,
            position=Position3D(0, 0, 0),
            orientation=orientation,
            sequence_number=1,
        ),
    )
    unpacked = (
        UnpackedUnit(
            load_unit_id=box.id,
            instance_number=2,
            reason_code="OUT_OF_BOUNDS",
            reason_message="No cupo en el espacio disponible.",
        ),
    )
    result = PackingResult(
        loading_space=space,
        placements=placements,
        unpacked_units=unpacked,
        requested_count=2,
        packed_count=1,
        used_volume_cm3=placements[0].volume_cm3,
        used_weight_kg=10.0,
        execution_time_seconds=1.234,
        algorithm_name="greedy_extreme_point_v1",
        warnings=("Aviso de prueba.",),
    )
    return result, {box.id: box}


def make_empty_result() -> tuple[PackingResult, dict]:
    """Un `PackingResult` sin productos, sin avisos — el "proyecto vacío" del encargo."""
    space = LoadingSpace(
        name="Bodega vacía",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(100, 100, 100),
    )
    result = PackingResult(
        loading_space=space,
        placements=(),
        unpacked_units=(),
        requested_count=0,
        packed_count=0,
        used_volume_cm3=0.0,
        used_weight_kg=0.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
    )
    return result, {}


def make_large_result(box_count: int = 60) -> tuple[PackingResult, dict]:
    """Un `PackingResult` con muchos productos cargados, para forzar varias páginas."""
    space = LoadingSpace(
        name="Contenedor 40'",
        category=LoadingSpaceCategory.CONTAINER,
        internal_dimensions=Dimensions3D(1200, 235, 239),
        max_weight_kg=28000.0,
    )
    box = LoadUnit(
        sku="SKU-BULK",
        name="Caja apilable",
        dimensions=Dimensions3D(30, 20, 20),
        weight_kg=5.0,
        quantity=box_count,
    )
    orientation = Orientation.from_base_dimensions(box.dimensions, OrientationCode.LWH_XYZ)
    placements = tuple(
        Placement(
            load_unit_id=box.id,
            instance_number=i + 1,
            position=Position3D(0, 0, 0),
            orientation=orientation,
            sequence_number=i + 1,
        )
        for i in range(box_count)
    )
    result = PackingResult(
        loading_space=space,
        placements=placements,
        unpacked_units=(),
        requested_count=box_count,
        packed_count=box_count,
        used_volume_cm3=sum(p.volume_cm3 for p in placements),
        used_weight_kg=box.weight_kg * box_count,
        execution_time_seconds=5.0,
        algorithm_name="greedy_extreme_point_v1",
    )
    return result, {box.id: box}
