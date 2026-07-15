"""Pruebas de `ProductCatalogTableModel` (fase 7.1), sin Qt real más allá de QAbstractTableModel."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.repositories import CatalogProductEntry
from cargo_optimizer.presentation.desktop.models.product_catalog_table_model import (
    COL_ACTIVE,
    COL_NAME,
    COL_SKU,
    ProductCatalogTableModel,
)


def _entry(**overrides: object) -> CatalogProductEntry:
    unit_kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    is_active = overrides.pop("is_active", True)
    unit_kwargs.update(overrides)
    unit = LoadUnit(**unit_kwargs)  # type: ignore[arg-type]
    return CatalogProductEntry(load_unit=unit, is_active=bool(is_active))


def test_starts_empty(qapp: object) -> None:
    model = ProductCatalogTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() > 0


def test_set_entries_populates_rows(qapp: object) -> None:
    model = ProductCatalogTableModel()
    model.set_entries([_entry(sku="BOX-1"), _entry(sku="BOX-2")])
    assert model.rowCount() == 2


def test_entry_at_returns_the_right_entry(qapp: object) -> None:
    model = ProductCatalogTableModel()
    entries = [_entry(sku="BOX-1"), _entry(sku="BOX-2")]
    model.set_entries(entries)
    assert model.entry_at(1).load_unit.sku == "BOX-2"


def test_data_shows_sku_name_and_active_status(qapp: object) -> None:
    from PySide6.QtCore import QModelIndex, Qt

    model = ProductCatalogTableModel()
    model.set_entries([_entry(sku="BOX-1", name="Caja uno", is_active=False)])

    def _index(column: int) -> QModelIndex:
        return model.index(0, column)

    assert model.data(_index(COL_SKU), Qt.ItemDataRole.DisplayRole) == "BOX-1"
    assert model.data(_index(COL_NAME), Qt.ItemDataRole.DisplayRole) == "Caja uno"
    assert "No" in model.data(_index(COL_ACTIVE), Qt.ItemDataRole.DisplayRole)
