"""Importación parcial y resolución de duplicados (fase 8.1).

Convierte una `CatalogImportPreview` ya calculada en un `ImportPlan`
final — qué filas se añaden y cuáles se actualizan — aplicando el modo
de selección (todas/seleccionadas/solo nuevas/solo actualizadas/solo
válidas) y, para cada SKU que ya existe en el catálogo, la resolución
elegida (Actualizar/Duplicar/Ignorar). Es una función pura: no escribe
nada en el catálogo — `ProductCatalogRepository.apply_bulk` (fase 8.1,
`infrastructure/database`) hace la escritura real, en una única
transacción.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Literal
from uuid import uuid4

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.import_preview import CatalogImportPreview

ImportSelectionMode = Literal["all", "selected", "new_only", "updated_only", "valid_only"]
DuplicateResolution = Literal["update", "duplicate", "ignore"]

_DEFAULT_DUPLICATE_SKU_SUFFIX = "-DUP"


@dataclass(frozen=True, slots=True)
class ImportPlan:
    """Filas finales a escribir en el catálogo, ya filtradas y con duplicados resueltos."""

    to_add: tuple[LoadUnit, ...]
    to_update: tuple[LoadUnit, ...]
    ignored_skus: tuple[str, ...]

    @property
    def total_count(self) -> int:
        return len(self.to_add) + len(self.to_update)


def build_import_plan(
    preview: CatalogImportPreview,
    resolve_sku: Callable[[str], LoadUnit | None],
    *,
    selection_mode: ImportSelectionMode = "all",
    selected_skus: frozenset[str] | None = None,
    duplicate_resolutions: Mapping[str, DuplicateResolution] | None = None,
    default_duplicate_resolution: DuplicateResolution = "update",
    duplicate_sku_suffix: str = _DEFAULT_DUPLICATE_SKU_SUFFIX,
) -> ImportPlan:
    """Construye el plan final de importación a partir de una vista previa ya clasificada.

    ``selection_mode="selected"`` filtra por ``selected_skus`` (SKU tal
    como aparecen en el archivo importado); el resto de modos ignoran
    ``selected_skus``. ``duplicate_resolutions`` es
    ``{sku: "update" | "duplicate" | "ignore"}`` — cualquier SKU
    existente que no tenga una entrada explícita usa
    ``default_duplicate_resolution`` (por defecto "update", el
    comportamiento menos sorprendente), lo que permite implementar
    "aplicar a todos" con un solo valor en vez de un mapa completo.
    """
    resolutions = duplicate_resolutions or {}

    def _is_selected(sku: str) -> bool:
        return selected_skus is None or sku in selected_skus

    to_add: list[LoadUnit] = []
    to_update: list[LoadUnit] = []
    ignored: list[str] = []

    include_new = selection_mode in ("all", "new_only", "valid_only", "selected")
    include_existing = selection_mode in ("all", "updated_only", "valid_only", "selected")

    if include_new:
        for unit in preview.new_units:
            if selection_mode == "selected" and not _is_selected(unit.sku):
                continue
            to_add.append(unit)

    if include_existing:
        for unit in preview.existing_units:
            if selection_mode == "selected" and not _is_selected(unit.sku):
                continue
            action = resolutions.get(unit.sku, default_duplicate_resolution)
            if action == "ignore":
                ignored.append(unit.sku)
            elif action == "duplicate":
                to_add.append(replace(unit, id=uuid4(), sku=f"{unit.sku}{duplicate_sku_suffix}"))
            else:  # "update"
                existing = resolve_sku(unit.sku)
                target_id = existing.id if existing is not None else unit.id
                to_update.append(replace(unit, id=target_id))

    return ImportPlan(to_add=tuple(to_add), to_update=tuple(to_update), ignored_skus=tuple(ignored))
