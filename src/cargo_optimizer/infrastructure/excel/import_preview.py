"""Vista previa de una importación de catálogo antes de escribir nada (fase 8.1).

Clasifica el resultado ya calculado por `catalog_importer.py`/`mapping.py`
en las cuatro categorías que pide un asistente de importación
profesional — nuevos, existentes, duplicados e inválidos — sin tocar
el catálogo. Los duplicados dentro del propio archivo ya llegan como
`RowError` desde el importador (mensaje que contiene "duplicado"); esta
vista previa solo los separa de los demás errores de fila para
mostrarlos en su propio contador.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.results import CatalogImportResult, RowError

_DUPLICATE_MARKER = "duplicado"


@dataclass(frozen=True, slots=True)
class CatalogImportPreview:
    """Resumen de una importación de catálogo, calculado sin escribir nada todavía."""

    row_count: int
    column_count: int
    new_units: tuple[LoadUnit, ...]
    existing_units: tuple[LoadUnit, ...]
    duplicate_errors: tuple[RowError, ...]
    invalid_errors: tuple[RowError, ...]

    @property
    def new_count(self) -> int:
        return len(self.new_units)

    @property
    def existing_count(self) -> int:
        return len(self.existing_units)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_errors)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_errors)


def build_catalog_preview(
    result: CatalogImportResult,
    resolve_sku: Callable[[str], LoadUnit | None],
    *,
    column_count: int,
) -> CatalogImportPreview:
    """Clasifica `result.units` en nuevos/existentes y `result.errors` en duplicados/inválidos.

    ``resolve_sku`` es normalmente ``CatalogService.products.get_by_sku``
    — igual patrón de función inyectada que ya usa
    `packing_list_importer.import_packing_list` para no depender de
    `infrastructure/database`.
    """
    new_units: list[LoadUnit] = []
    existing_units: list[LoadUnit] = []
    for unit in result.units:
        if resolve_sku(unit.sku) is None:
            new_units.append(unit)
        else:
            existing_units.append(unit)

    duplicate_errors = tuple(
        error for error in result.errors if _DUPLICATE_MARKER in error.message.casefold()
    )
    invalid_errors = tuple(
        error for error in result.errors if _DUPLICATE_MARKER not in error.message.casefold()
    )

    return CatalogImportPreview(
        row_count=len(result.units) + len(result.errors),
        column_count=column_count,
        new_units=tuple(new_units),
        existing_units=tuple(existing_units),
        duplicate_errors=duplicate_errors,
        invalid_errors=invalid_errors,
    )
