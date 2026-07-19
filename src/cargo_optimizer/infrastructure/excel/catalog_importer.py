"""Importar un catálogo completo de `LoadUnit` desde un `.xlsx`.

Nunca importa una fila inválida en silencio: cada fila se valida por
completo contra `LoadUnit` (`domain`), y cualquier fallo —de formato o
de invariante de dominio— se recoge como un `RowError` con su número de
fila, nunca se descarta. Un SKU repetido dentro del propio archivo
también se trata como error de fila (el catálogo exige SKU único).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from openpyxl.worksheet.worksheet import Worksheet

from cargo_optimizer.infrastructure.excel.product_rows import (
    EXAMPLE_ROW_SKU_MARKER,
    PRODUCT_COLUMNS,
    row_to_load_unit,
)
from cargo_optimizer.infrastructure.excel.results import CatalogImportResult, RowError
from cargo_optimizer.infrastructure.excel.row_parsing import RowConversionError
from cargo_optimizer.infrastructure.excel.workbook_utils import (
    get_active_worksheet,
    iter_data_rows,
    open_workbook,
    require_headers,
)


def import_catalog(path: Path, *, existing_colors: Sequence[str] = ()) -> CatalogImportResult:
    """Lee un archivo con el formato de `CatalogTemplate.xlsx` y devuelve el resultado.

    Nunca lanza por filas inválidas: esas se acumulan en
    ``result.errors``. Solo lanza `ExcelFileError` (archivo corrupto) o
    `ExcelTemplateError` (no coincide con la plantilla) — errores que
    impiden leer el archivo en absoluto, no un problema de una fila.

    `existing_colors` (fase OPT-18, opcional): colores ya en uso fuera
    de este archivo (p. ej. el catálogo real) para que la sugerencia de
    color pastel de una celda vacía también los evite, además de los
    colores ya vistos dentro del propio archivo. Ver
    `import_catalog_from_worksheet`.
    """
    workbook = open_workbook(path)
    worksheet = get_active_worksheet(workbook)
    require_headers(worksheet, PRODUCT_COLUMNS)
    return import_catalog_from_worksheet(worksheet, existing_colors=existing_colors)


def import_catalog_from_worksheet(
    worksheet: Worksheet, *, existing_colors: Sequence[str] = ()
) -> CatalogImportResult:
    """Igual que `import_catalog`, pero sobre una hoja ya abierta con cabeceras canónicas.

    Usado por `mapping.py` (fase 8.1) tras remapear las cabeceras de un
    archivo con un formato distinto al oficial — evita duplicar el
    bucle de conversión fila a fila.

    La fila de ejemplo de la plantilla oficial descargable
    (`templates.py::generate_product_import_template`, fase OPT-18) usa
    el SKU reservado `EXAMPLE_ROW_SKU_MARKER`: se omite aquí en
    silencio (ni se importa ni se cuenta como error), así que un usuario
    que olvide borrarla antes de importar nunca crea un producto real
    con ella.

    `existing_colors` se acumula con cada color (explícito o pastel ya
    asignado) a medida que se procesan filas, para que las celdas de
    color vacías de filas posteriores del mismo archivo eviten también
    los colores recién asignados, no solo los que ya existían antes de
    empezar a leer.
    """
    units = []
    errors: list[RowError] = []
    seen_skus: dict[str, int] = {}
    colors_in_use: list[str] = list(existing_colors)
    for row_number, values in iter_data_rows(worksheet, column_count=len(PRODUCT_COLUMNS)):
        raw_sku = values[0]
        if raw_sku is not None and str(raw_sku).strip().casefold() == (
            EXAMPLE_ROW_SKU_MARKER.casefold()
        ):
            continue
        try:
            unit = row_to_load_unit(row_number, values, existing_colors=colors_in_use)
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
        colors_in_use.append(unit.color_hex)
        units.append(unit)

    return CatalogImportResult(units=tuple(units), errors=tuple(errors))
