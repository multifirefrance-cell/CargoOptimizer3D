"""Resultados tipados de una importación desde Excel.

Ninguna fila inválida se importa en silencio (ver `docs/Excel.md`):
cada importador devuelve, junto con las entidades reconstruidas
correctamente, la lista completa de errores por fila
(`RowError.row_number` es el número de fila tal como lo vería un
usuario abriendo el archivo en Excel, cabecera incluida) para que la
capa de presentación los muestre siempre, nunca los descarte.
"""

from __future__ import annotations

from dataclasses import dataclass

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace


@dataclass(frozen=True, slots=True)
class RowError:
    """Un error de validación anclado a una fila concreta del archivo Excel."""

    row_number: int
    message: str


@dataclass(frozen=True, slots=True)
class CatalogImportResult:
    """Resultado de importar un `CatalogTemplate.xlsx` (o compatible)."""

    units: tuple[LoadUnit, ...]
    errors: tuple[RowError, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(frozen=True, slots=True)
class LoadingSpaceImportResult:
    """Resultado de importar un `LoadingSpaceTemplate.xlsx` (o compatible)."""

    spaces: tuple[LoadingSpace, ...]
    errors: tuple[RowError, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(frozen=True, slots=True)
class PackingListImportResult:
    """Resultado de importar un `PackingListTemplate.xlsx` (o compatible).

    ``resolved_units`` son copias independientes (UUID nuevo) del
    `LoadUnit` del catálogo, con la cantidad tomada del packing list
    aplicada — mismo criterio de copia independiente que
    `CatalogService.copy_to_project` (fase 7.1): nunca quedan ligadas
    al catálogo. ``missing_skus`` son los SKU del archivo que no se
    encontraron en el catálogo (a decisión de la interfaz: Continuar
    ignorándolos o Cancelar la importación completa).
    """

    resolved_units: tuple[LoadUnit, ...]
    missing_skus: tuple[str, ...]
    errors: tuple[RowError, ...]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def has_missing_skus(self) -> bool:
        return bool(self.missing_skus)
