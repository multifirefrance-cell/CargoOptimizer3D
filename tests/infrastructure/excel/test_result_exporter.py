"""Pruebas de `result_exporter.py`: las cinco hojas, contenido correcto, sin macros."""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.infrastructure.excel.result_exporter import (
    SHEET_PACKED,
    SHEET_SPACE,
    SHEET_SUMMARY,
    SHEET_UNPACKED,
    SHEET_WARNINGS,
    export_packing_result,
)


def _sample_result() -> tuple[PackingResult, dict]:
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(500, 200, 200),
        max_weight_kg=5000.0,
    )
    box = LoadUnit(
        sku="SKU-1", name="Caja", dimensions=Dimensions3D(50, 40, 30), weight_kg=10.0, quantity=2
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


def test_export_creates_the_five_expected_sheets(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"

    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    workbook = load_workbook(path)
    assert workbook.sheetnames == [
        SHEET_SUMMARY,
        SHEET_PACKED,
        SHEET_UNPACKED,
        SHEET_WARNINGS,
        SHEET_SPACE,
    ]


def test_summary_sheet_contains_algorithm_and_percentages(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"
    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    worksheet = load_workbook(path)[SHEET_SUMMARY]
    values = {
        row[0]: row[1]
        for row in worksheet.iter_rows(min_row=3, max_col=2, values_only=True)
        if row[0]
    }
    assert values["Algoritmo utilizado"] == "greedy_extreme_point_v1"
    assert values["Unidades solicitadas"] == 2
    assert values["Unidades cargadas"] == 1
    assert values["Generado con CargoOptimizer3D version"] == "9.9.9"


def test_packed_sheet_resolves_sku_and_name(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"
    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    worksheet = load_workbook(path)[SHEET_PACKED]
    row = next(worksheet.iter_rows(min_row=2, max_row=2, values_only=True))
    assert row[0] == "SKU-1"
    assert row[1] == "Caja"


def test_unpacked_sheet_has_reason(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"
    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    worksheet = load_workbook(path)[SHEET_UNPACKED]
    row = next(worksheet.iter_rows(min_row=2, max_row=2, values_only=True))
    assert row[0] == "SKU-1"
    assert row[3] == "OUT_OF_BOUNDS"


def test_warnings_sheet_lists_every_warning(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"
    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    worksheet = load_workbook(path)[SHEET_WARNINGS]
    row = next(worksheet.iter_rows(min_row=2, max_row=2, values_only=True))
    assert row[0] == "Aviso de prueba."


def test_space_sheet_has_dimensions_and_no_weight_limit(tmp_path: Path) -> None:
    result, load_units_by_id = _sample_result()
    path = tmp_path / "resultado.xlsx"
    export_packing_result(result, load_units_by_id, path, application_version="9.9.9")

    worksheet = load_workbook(path)[SHEET_SPACE]
    values = {
        row[0]: row[1]
        for row in worksheet.iter_rows(min_row=3, max_col=2, values_only=True)
        if row[0]
    }
    assert values["Nombre"] == "Espacio de prueba"
    assert values["Peso maximo (kg)"] == 5000.0


def test_export_handles_a_result_with_no_placements_or_warnings(tmp_path: Path) -> None:
    space = LoadingSpace(
        name="Vacio",
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
    path = tmp_path / "vacio.xlsx"

    export_packing_result(result, {}, path, application_version="9.9.9")

    workbook = load_workbook(path)
    assert workbook.sheetnames == [
        SHEET_SUMMARY,
        SHEET_PACKED,
        SHEET_UNPACKED,
        SHEET_WARNINGS,
        SHEET_SPACE,
    ]
    assert workbook[SHEET_SPACE]["B10"].value == "Sin limite declarado"
