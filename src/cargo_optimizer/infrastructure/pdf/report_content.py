"""Traducción de `domain` a los datos neutrales que muestra un informe PDF.

`ReportContent` es la única estructura que ve `sections.py`/
`report_builder.py`; ningún otro módulo de `infrastructure/pdf` importa
`domain` directamente — ver `docs/PdfReportDesign.md`, sección 2. Las
etiquetas en español de categoría/posición de puerta/orientación son
una copia deliberada e independiente de las de
`infrastructure/excel/loading_space_rows.py`/`product_rows.py`:
`infrastructure/pdf` nunca importa `infrastructure/excel` (mismo
criterio que ya evita el acoplo infra-a-infra en la fase 8.1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit

CATEGORY_LABELS: dict[LoadingSpaceCategory, str] = {
    LoadingSpaceCategory.CONTAINER: "Contenedor",
    LoadingSpaceCategory.TRUCK: "Camión",
    LoadingSpaceCategory.VAN: "Van",
    LoadingSpaceCategory.TRAILER: "Semirremolque",
    LoadingSpaceCategory.WAREHOUSE: "Bodega",
    LoadingSpaceCategory.RACK: "Rack",
    LoadingSpaceCategory.OTHER: "Otro",
}

DOOR_POSITION_LABELS: dict[DoorPosition, str] = {
    DoorPosition.FRONT: "Frontal",
    DoorPosition.REAR: "Trasera",
    DoorPosition.LEFT: "Izquierda",
    DoorPosition.RIGHT: "Derecha",
    DoorPosition.TOP: "Superior",
    DoorPosition.UNRESTRICTED: "Sin restricción",
}

ORIENTATION_LABELS: dict[OrientationCode, str] = {
    OrientationCode.LWH_XYZ: "Original",
    OrientationCode.WLH_XYZ: "Girada 90° Z",
    OrientationCode.LHW_XYZ: "Girada 90° X",
    OrientationCode.HWL_XYZ: "Girada 90° Y",
    OrientationCode.WHL_XYZ: "Ancho-alto-largo",
    OrientationCode.HLW_XYZ: "Alto-largo-ancho",
}

_UNKNOWN_PRODUCT_LABEL = "(producto desconocido)"


@dataclass(frozen=True, slots=True)
class ProductRow:
    """Una fila de la tabla de productos cargados."""

    sku: str
    name: str
    instance_number: int
    position_x_cm: float
    position_y_cm: float
    position_z_cm: float
    orientation_label: str
    length_cm: float
    width_cm: float
    height_cm: float
    sequence_number: int


@dataclass(frozen=True, slots=True)
class UnpackedRow:
    """Una fila de la tabla de productos no cargados."""

    sku: str
    name: str
    instance_number: int
    reason_code: str
    reason_message: str


@dataclass(frozen=True, slots=True)
class ReportContent:
    """Todo lo que un informe puede necesitar mostrar, ya resuelto — sin tipos de `reportlab`."""

    project_name: str
    generated_at: datetime
    application_version: str
    algorithm_name: str
    execution_time_seconds: float
    requested_count: int
    packed_count: int
    unpacked_count: int
    packing_completion_percent: float
    volume_utilization_percent: float
    weight_utilization_percent: float | None
    used_volume_cm3: float
    used_weight_kg: float
    space_name: str
    space_category_label: str
    space_length_cm: float
    space_width_cm: float
    space_height_cm: float
    space_max_weight_kg: float | None
    space_door_position_label: str
    space_notes: str
    packed_rows: tuple[ProductRow, ...]
    unpacked_rows: tuple[UnpackedRow, ...]
    warnings: tuple[str, ...]
    viewer_screenshot_png: bytes | None = None


def _resolve_unit_label(
    load_units_by_id: Mapping[UUID, LoadUnit], unit_id: UUID
) -> tuple[str, str]:
    unit = load_units_by_id.get(unit_id)
    if unit is None:
        return (str(unit_id), _UNKNOWN_PRODUCT_LABEL)
    return (unit.sku, unit.name)


def _build_product_row(
    placement: Placement, load_units_by_id: Mapping[UUID, LoadUnit]
) -> ProductRow:
    sku, name = _resolve_unit_label(load_units_by_id, placement.load_unit_id)
    return ProductRow(
        sku=sku,
        name=name,
        instance_number=placement.instance_number,
        position_x_cm=placement.x_cm,
        position_y_cm=placement.y_cm,
        position_z_cm=placement.z_cm,
        orientation_label=ORIENTATION_LABELS[placement.orientation.code],
        length_cm=placement.length_cm,
        width_cm=placement.width_cm,
        height_cm=placement.height_cm,
        sequence_number=placement.sequence_number,
    )


def _build_unpacked_row(
    unit: UnpackedUnit, load_units_by_id: Mapping[UUID, LoadUnit]
) -> UnpackedRow:
    sku, name = _resolve_unit_label(load_units_by_id, unit.load_unit_id)
    return UnpackedRow(
        sku=sku,
        name=name,
        instance_number=unit.instance_number,
        reason_code=unit.reason_code,
        reason_message=unit.reason_message,
    )


def build_report_content(
    result: PackingResult,
    load_units_by_id: Mapping[UUID, LoadUnit],
    *,
    project_name: str,
    application_version: str,
    viewer_screenshot_png: bytes | None = None,
) -> ReportContent:
    """Construye el `ReportContent` de un `PackingResult` ya calculado.

    Único punto de `infrastructure/pdf` que importa `domain` — ver
    `docs/PdfReportDesign.md`, sección 2. ``viewer_screenshot_png`` se
    recibe ya capturado (o `None`); esta función nunca intenta generarlo.
    """
    space = result.loading_space

    packed_rows = tuple(
        sorted(
            (_build_product_row(p, load_units_by_id) for p in result.placements),
            key=lambda row: row.sequence_number,
        )
    )
    unpacked_rows = tuple(_build_unpacked_row(u, load_units_by_id) for u in result.unpacked_units)

    return ReportContent(
        project_name=project_name,
        generated_at=datetime.now(UTC),
        application_version=application_version,
        algorithm_name=result.algorithm_name,
        execution_time_seconds=result.execution_time_seconds,
        requested_count=result.requested_count,
        packed_count=result.packed_count,
        unpacked_count=result.unpacked_count,
        packing_completion_percent=result.packing_completion_percent,
        volume_utilization_percent=result.volume_utilization_percent,
        weight_utilization_percent=result.weight_utilization_percent,
        used_volume_cm3=result.used_volume_cm3,
        used_weight_kg=result.used_weight_kg,
        space_name=space.name,
        space_category_label=CATEGORY_LABELS[space.category],
        space_length_cm=space.internal_dimensions.length_cm,
        space_width_cm=space.internal_dimensions.width_cm,
        space_height_cm=space.internal_dimensions.height_cm,
        space_max_weight_kg=space.max_weight_kg,
        space_door_position_label=DOOR_POSITION_LABELS[space.door_position],
        space_notes=space.notes,
        packed_rows=packed_rows,
        unpacked_rows=unpacked_rows,
        warnings=result.warnings,
        viewer_screenshot_png=viewer_screenshot_png,
    )
