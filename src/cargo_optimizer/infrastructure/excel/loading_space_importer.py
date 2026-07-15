"""Importar perfiles de Loading Space (contenedores, camiones, vans, bodegas,
espacios personalizados) desde un `.xlsx`.

Nunca importa una fila inválida en silencio: cada fila se valida por
completo contra `LoadingSpace` (`domain`); cualquier fallo se recoge
como un `RowError` con su número de fila.
"""

from __future__ import annotations

from pathlib import Path

from cargo_optimizer.infrastructure.excel.loading_space_rows import (
    LOADING_SPACE_COLUMNS,
    row_to_loading_space,
)
from cargo_optimizer.infrastructure.excel.results import LoadingSpaceImportResult, RowError
from cargo_optimizer.infrastructure.excel.row_parsing import RowConversionError
from cargo_optimizer.infrastructure.excel.workbook_utils import (
    get_active_worksheet,
    iter_data_rows,
    open_workbook,
    require_headers,
)


def import_loading_spaces(path: Path) -> LoadingSpaceImportResult:
    """Lee un archivo con el formato de `LoadingSpaceTemplate.xlsx` y devuelve el resultado."""
    workbook = open_workbook(path)
    worksheet = get_active_worksheet(workbook)
    require_headers(worksheet, LOADING_SPACE_COLUMNS)

    spaces = []
    errors: list[RowError] = []
    for row_number, values in iter_data_rows(worksheet, column_count=len(LOADING_SPACE_COLUMNS)):
        try:
            spaces.append(row_to_loading_space(row_number, values))
        except RowConversionError as exc:
            errors.append(RowError(row_number, exc.message))

    return LoadingSpaceImportResult(spaces=tuple(spaces), errors=tuple(errors))
