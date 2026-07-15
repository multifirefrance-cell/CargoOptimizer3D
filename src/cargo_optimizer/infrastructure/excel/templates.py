"""Generación de las cuatro plantillas oficiales de CargoOptimizer3D.

Cada plantilla se construye con el propio código de exportación del
paquete (nunca escrita a mano celda a celda fuera de aquí), igual que
`examples/example_project.cargo3d` se generó con el `ProjectFileRepository`
real en la fase 7.0: la plantilla que se distribuye es exactamente lo
que el programa produciría, garantizando que nunca se desincroniza del
formato real.

`infrastructure/excel` depende únicamente de `domain` (igual que
`infrastructure/persistence` e `infrastructure/database`): el ejemplo
de `OptimizationResultTemplate.xlsx` construye un `PackingResult`
ilustrativo directamente con los constructores de dominio, sin invocar
`PackingEngine` — no hace falta ejecutar el optimizador real para
mostrar el formato de la hoja de resultados.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from openpyxl import Workbook

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    DoorPosition,
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.infrastructure.excel.catalog_exporter import export_catalog
from cargo_optimizer.infrastructure.excel.loading_space_rows import (
    LOADING_SPACE_COLUMNS,
    LOADING_SPACE_SHEET_NAME,
    loading_space_to_row,
)
from cargo_optimizer.infrastructure.excel.packing_list_importer import PACKING_LIST_COLUMNS
from cargo_optimizer.infrastructure.excel.result_exporter import export_packing_result
from cargo_optimizer.infrastructure.excel.styles import (
    apply_borders_to_data_rows,
    apply_table,
    autofit_columns,
    write_header_row,
)
from cargo_optimizer.infrastructure.excel.workbook_utils import (
    HEADER_ROW,
    get_active_worksheet,
    save_workbook_atomic,
)

CATALOG_TEMPLATE_FILENAME = "CatalogTemplate.xlsx"
PACKING_LIST_TEMPLATE_FILENAME = "PackingListTemplate.xlsx"
LOADING_SPACE_TEMPLATE_FILENAME = "LoadingSpaceTemplate.xlsx"
OPTIMIZATION_RESULT_TEMPLATE_FILENAME = "OptimizationResultTemplate.xlsx"

_PACKING_LIST_SHEET_NAME = "Packing List"


def _example_catalog_units() -> tuple[LoadUnit, ...]:
    return (
        LoadUnit(
            sku="CAJA-001",
            name="Caja de electronica",
            dimensions=Dimensions3D(length_cm=60, width_cm=40, height_cm=35),
            weight_kg=12.5,
            quantity=20,
            fragile=True,
            notes="Ejemplo: producto individual fragil.",
        ),
        LoadUnit(
            sku="PALLET-002",
            name="Pallet de repuestos",
            dimensions=Dimensions3D(length_cm=120, width_cm=100, height_cm=110),
            weight_kg=350.0,
            quantity=4,
            max_stack_count=2,
            allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
            notes="Ejemplo: pallet, apilable hasta 2 niveles.",
        ),
        LoadUnit(
            sku="EXT-CO2-05",
            name="Extintor CO2 5kg",
            dimensions=Dimensions3D(length_cm=20, width_cm=20, height_cm=60),
            weight_kg=8.0,
            quantity=6,
            is_extinguisher=True,
            extinguisher_agent=ExtinguisherAgent.CO2,
            extinguisher_nominal_kg=5.0,
            allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
            max_stack_count=1,
            notes="Ejemplo: extintor individual, siempre horizontal.",
        ),
    )


def generate_catalog_template(path: Path) -> None:
    """Genera `CatalogTemplate.xlsx`: cabeceras reales + filas de ejemplo."""
    export_catalog(_example_catalog_units(), path)


def generate_packing_list_template(path: Path) -> None:
    """Genera `PackingListTemplate.xlsx`: SKU + Cantidad, con ejemplos de `CatalogTemplate.xlsx`."""
    workbook = Workbook()
    worksheet = get_active_worksheet(workbook)
    worksheet.title = _PACKING_LIST_SHEET_NAME

    write_header_row(worksheet, PACKING_LIST_COLUMNS, row=HEADER_ROW)
    example_rows = (("CAJA-001", 20), ("PALLET-002", 4), ("EXT-CO2-05", 6))
    last_row = HEADER_ROW
    for row_values in example_rows:
        last_row += 1
        worksheet.append(row_values)

    column_count = len(PACKING_LIST_COLUMNS)
    apply_borders_to_data_rows(
        worksheet, first_row=HEADER_ROW, last_row=last_row, column_count=column_count
    )
    apply_table(
        worksheet,
        table_name="TablaPackingList",
        first_row=HEADER_ROW + 1,
        last_row=last_row,
        column_count=column_count,
    )
    autofit_columns(worksheet, column_count=column_count)

    save_workbook_atomic(workbook, path)


def _example_loading_spaces() -> tuple[LoadingSpace, ...]:
    return (
        LoadingSpace.standard_20ft_container(),
        LoadingSpace.standard_40ft_container(),
        LoadingSpace(
            name="Bodega generica 500 m2",
            category=LoadingSpaceCategory.WAREHOUSE,
            internal_dimensions=Dimensions3D(length_cm=2500, width_cm=2000, height_cm=600),
            door_position=DoorPosition.UNRESTRICTED,
            max_weight_kg=None,
            notes="Ejemplo: espacio personalizado, sin limite de peso declarado.",
        ),
    )


def generate_loading_space_template(path: Path) -> None:
    """Genera `LoadingSpaceTemplate.xlsx`: perfiles de ejemplo (contenedor, bodega)."""
    workbook = Workbook()
    worksheet = get_active_worksheet(workbook)
    worksheet.title = LOADING_SPACE_SHEET_NAME

    write_header_row(worksheet, LOADING_SPACE_COLUMNS, row=HEADER_ROW)
    last_row = HEADER_ROW
    for space in _example_loading_spaces():
        last_row += 1
        worksheet.append(loading_space_to_row(space))

    column_count = len(LOADING_SPACE_COLUMNS)
    apply_borders_to_data_rows(
        worksheet, first_row=HEADER_ROW, last_row=last_row, column_count=column_count
    )
    apply_table(
        worksheet,
        table_name="TablaEspaciosDeCarga",
        first_row=HEADER_ROW + 1,
        last_row=last_row,
        column_count=column_count,
    )
    autofit_columns(worksheet, column_count=column_count)

    save_workbook_atomic(workbook, path)


def _example_packing_result() -> tuple[PackingResult, dict[UUID, LoadUnit]]:
    space = LoadingSpace.standard_20ft_container()
    box = LoadUnit(
        sku="CAJA-001",
        name="Caja de electronica",
        dimensions=Dimensions3D(length_cm=60, width_cm=40, height_cm=35),
        weight_kg=12.5,
        quantity=3,
        fragile=True,
    )
    pallet = LoadUnit(
        sku="PALLET-002",
        name="Pallet de repuestos",
        dimensions=Dimensions3D(length_cm=120, width_cm=100, height_cm=110),
        weight_kg=350.0,
        quantity=1,
        max_stack_count=2,
    )
    orientation = Orientation.from_base_dimensions(box.dimensions, OrientationCode.LWH_XYZ)
    pallet_orientation = Orientation.from_base_dimensions(
        pallet.dimensions, OrientationCode.LWH_XYZ
    )
    placements = (
        Placement(
            load_unit_id=box.id,
            instance_number=1,
            position=Position3D(0, 0, 0),
            orientation=orientation,
            sequence_number=1,
        ),
        Placement(
            load_unit_id=box.id,
            instance_number=2,
            position=Position3D(60, 0, 0),
            orientation=orientation,
            sequence_number=2,
        ),
        Placement(
            load_unit_id=pallet.id,
            instance_number=1,
            position=Position3D(0, 40, 0),
            orientation=pallet_orientation,
            sequence_number=3,
        ),
    )
    unpacked = (
        UnpackedUnit(
            load_unit_id=box.id,
            instance_number=3,
            reason_code="OUT_OF_BOUNDS",
            reason_message="No quedo espacio disponible dentro del Loading Space.",
        ),
    )
    used_volume = sum(p.volume_cm3 for p in placements)
    used_weight = box.weight_kg * 2 + pallet.weight_kg
    result = PackingResult(
        loading_space=space,
        placements=placements,
        unpacked_units=unpacked,
        requested_count=4,
        packed_count=3,
        used_volume_cm3=used_volume,
        used_weight_kg=used_weight,
        execution_time_seconds=0.842,
        algorithm_name="greedy_extreme_point_v1 (ejemplo ilustrativo)",
        warnings=(
            "Ejemplo generado para la plantilla oficial, no proviene de una optimizacion real.",
        ),
    )
    load_units_by_id = {box.id: box, pallet.id: pallet}
    return result, load_units_by_id


def generate_optimization_result_template(path: Path, *, application_version: str) -> None:
    """Genera `OptimizationResultTemplate.xlsx` con un `PackingResult` ilustrativo."""
    result, load_units_by_id = _example_packing_result()
    export_packing_result(result, load_units_by_id, path, application_version=application_version)


def generate_all_templates(directory: Path, *, application_version: str) -> tuple[Path, ...]:
    """Genera las cuatro plantillas oficiales dentro de `directory`."""
    directory.mkdir(parents=True, exist_ok=True)
    catalog_path = directory / CATALOG_TEMPLATE_FILENAME
    packing_list_path = directory / PACKING_LIST_TEMPLATE_FILENAME
    loading_space_path = directory / LOADING_SPACE_TEMPLATE_FILENAME
    result_path = directory / OPTIMIZATION_RESULT_TEMPLATE_FILENAME

    generate_catalog_template(catalog_path)
    generate_packing_list_template(packing_list_path)
    generate_loading_space_template(loading_space_path)
    generate_optimization_result_template(result_path, application_version=application_version)

    return (catalog_path, packing_list_path, loading_space_path, result_path)
