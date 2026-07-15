"""Exportar una colección de `LoadUnit` (catálogo o productos de un proyecto) a `.xlsx`.

Formato profesional: cabecera en negrita con relleno suave, bordes,
autoajuste de columnas y una tabla nativa de Excel — sin macros, sin
VBA (ver `docs/Excel.md`).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.product_rows import (
    CATALOG_SHEET_NAME,
    PRODUCT_COLUMNS,
    load_unit_to_row,
)
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

_TABLE_NAME = "TablaCatalogo"


def export_catalog(units: Iterable[LoadUnit], path: Path) -> None:
    """Escribe `units` (en el orden recibido) a `path` con el formato de `CatalogTemplate.xlsx`."""
    workbook = Workbook()
    worksheet = get_active_worksheet(workbook)
    worksheet.title = CATALOG_SHEET_NAME

    write_header_row(worksheet, PRODUCT_COLUMNS, row=HEADER_ROW)
    last_row = HEADER_ROW
    for unit in units:
        last_row += 1
        worksheet.append(load_unit_to_row(unit))

    column_count = len(PRODUCT_COLUMNS)
    apply_borders_to_data_rows(
        worksheet, first_row=HEADER_ROW, last_row=last_row, column_count=column_count
    )
    apply_table(
        worksheet,
        table_name=_TABLE_NAME,
        first_row=HEADER_ROW + 1,
        last_row=last_row,
        column_count=column_count,
    )
    autofit_columns(worksheet, column_count=column_count)

    save_workbook_atomic(workbook, path)
