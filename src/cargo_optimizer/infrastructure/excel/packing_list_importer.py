"""Importar un Packing List (SKU + Cantidad) desde un `.xlsx`.

No conoce SQLite ni `CatalogService` directamente — igual que
`optimization` nunca conoce Qt (ver `CLAUDE.md`), este importador no
depende de `infrastructure/database`: recibe un `resolve_sku` que la
capa de presentación conecta a
`CatalogService.products.get_by_sku`. Esto mantiene
`infrastructure/excel` independiente y comprobable sin una base de
datos real.

Un mismo SKU repetido en varias filas de un packing list es una
situación normal en logística (líneas de picking distintas para el
mismo artículo): las cantidades se suman en vez de tratarse como error
— a diferencia del catálogo, donde el SKU debe ser único.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.results import PackingListImportResult, RowError
from cargo_optimizer.infrastructure.excel.workbook_utils import (
    get_active_worksheet,
    iter_data_rows,
    open_workbook,
    require_headers,
)

PACKING_LIST_COLUMNS: tuple[str, ...] = ("SKU", "Cantidad")


def import_packing_list(
    path: Path, resolve_sku: Callable[[str], LoadUnit | None]
) -> PackingListImportResult:
    """Lee un archivo con el formato de `PackingListTemplate.xlsx`.

    Para cada SKU encontrado en el archivo llama a ``resolve_sku`` (una
    búsqueda de catálogo real, normalmente
    ``CatalogService.products.get_by_sku``). Los SKU que no resuelven
    se acumulan en ``missing_skus`` — nunca se lanza una excepción por
    esto: es una decisión de la interfaz (Continuar/Cancelar), no un
    error del importador.
    """
    workbook = open_workbook(path)
    worksheet = get_active_worksheet(workbook)
    require_headers(worksheet, PACKING_LIST_COLUMNS)

    quantities_by_sku: dict[str, int] = {}
    original_case_by_sku: dict[str, str] = {}
    errors: list[RowError] = []
    missing: list[str] = []
    seen_missing: set[str] = set()

    for row_number, values in iter_data_rows(worksheet, column_count=len(PACKING_LIST_COLUMNS)):
        sku_raw, quantity_raw = values
        sku = "" if sku_raw is None else str(sku_raw).strip()
        if not sku:
            errors.append(RowError(row_number, "'SKU' no puede estar vacío."))
            continue
        try:
            quantity = int(float(quantity_raw))
            if quantity < 1:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(
                RowError(row_number, f"'Cantidad' inválida para el SKU '{sku}': '{quantity_raw}'.")
            )
            continue

        key = sku.casefold()
        original_case_by_sku.setdefault(key, sku)
        quantities_by_sku[key] = quantities_by_sku.get(key, 0) + quantity

    resolved_units: list[LoadUnit] = []
    for key, quantity in quantities_by_sku.items():
        sku = original_case_by_sku[key]
        catalog_unit = resolve_sku(sku)
        if catalog_unit is None:
            if key not in seen_missing:
                seen_missing.add(key)
                missing.append(sku)
            continue
        resolved_units.append(replace(catalog_unit, id=uuid4(), quantity=quantity))

    return PackingListImportResult(
        resolved_units=tuple(resolved_units),
        missing_skus=tuple(missing),
        errors=tuple(errors),
    )
