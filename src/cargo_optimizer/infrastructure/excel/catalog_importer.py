"""Importar un catálogo completo de `LoadUnit` desde un `.xlsx`.

Nunca importa una fila inválida en silencio: cada fila se valida por
completo contra `LoadUnit` (`domain`), y cualquier fallo —de formato o
de invariante de dominio— se recoge como un `RowError` con su número de
fila, nunca se descarta. Un SKU repetido dentro del propio archivo
también se trata como error de fila (el catálogo exige SKU único).
"""

from __future__ import annotations

from pathlib import Path

from cargo_optimizer.infrastructure.excel.product_rows import PRODUCT_COLUMNS, row_to_load_unit
from cargo_optimizer.infrastructure.excel.results import CatalogImportResult, RowError
from cargo_optimizer.infrastructure.excel.row_parsing import RowConversionError
from cargo_optimizer.infrastructure.excel.workbook_utils import (
    get_active_worksheet,
    iter_data_rows,
    open_workbook,
    require_headers,
)


def import_catalog(path: Path) -> CatalogImportResult:
    """Lee un archivo con el formato de `CatalogTemplate.xlsx` y devuelve el resultado.

    Nunca lanza por filas inválidas: esas se acumulan en
    ``result.errors``. Solo lanza `ExcelFileError` (archivo corrupto) o
    `ExcelTemplateError` (no coincide con la plantilla) — errores que
    impiden leer el archivo en absoluto, no un problema de una fila.
    """
    workbook = open_workbook(path)
    worksheet = get_active_worksheet(workbook)
    require_headers(worksheet, PRODUCT_COLUMNS)

    units = []
    errors: list[RowError] = []
    seen_skus: dict[str, int] = {}
    for row_number, values in iter_data_rows(worksheet, column_count=len(PRODUCT_COLUMNS)):
        try:
            unit = row_to_load_unit(row_number, values)
        except RowConversionError as exc:
            errors.append(RowError(row_number, exc.message))
            continue
        existing_row = seen_skus.get(unit.sku.casefold())
        if existing_row is not None:
            errors.append(
                RowError(
                    row_number,
                    f"SKU duplicado en el archivo: '{unit.sku}' "
                    f"(ya aparece en la fila {existing_row}).",
                )
            )
            continue
        seen_skus[unit.sku.casefold()] = row_number
        units.append(unit)

    return CatalogImportResult(units=tuple(units), errors=tuple(errors))
