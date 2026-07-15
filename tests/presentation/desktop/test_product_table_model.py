"""Pruebas de `ProductTableModel`."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.models.product_table_model import (
    COL_EXTINGUISHER,
    COL_FRAGILE,
    COL_NAME,
    COL_QUANTITY,
    COL_SKU,
    ProductTableModel,
)


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def test_empty_model_has_no_rows(qapp: QApplication) -> None:
    model = ProductTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 14


def test_model_starts_with_given_load_units(qapp: QApplication) -> None:
    model = ProductTableModel([_unit(sku="A"), _unit(sku="B")])
    assert model.rowCount() == 2
    assert model.load_units()[0].sku == "A"
    assert model.load_units()[1].sku == "B"


def test_display_data_matches_load_unit_fields(qapp: QApplication) -> None:
    model = ProductTableModel([_unit(sku="SKU-X", name="Producto X", quantity=5)])
    sku_index = model.index(0, COL_SKU)
    name_index = model.index(0, COL_NAME)
    quantity_index = model.index(0, COL_QUANTITY)

    assert model.data(sku_index) == "SKU-X"
    assert model.data(name_index) == "Producto X"
    assert model.data(quantity_index) == 5


def test_header_data_returns_spanish_labels(qapp: QApplication) -> None:
    model = ProductTableModel()
    assert model.headerData(COL_SKU, Qt.Orientation.Horizontal) == "SKU"
    assert model.headerData(COL_NAME, Qt.Orientation.Horizontal) == "Nombre"


def test_add_default_product_appends_row(qapp: QApplication) -> None:
    model = ProductTableModel()
    model.add_default_product()
    assert model.rowCount() == 1
    assert model.load_units()[0].sku.startswith("SKU-")


def test_remove_rows_at_deletes_selected_rows(qapp: QApplication) -> None:
    model = ProductTableModel([_unit(sku="A"), _unit(sku="B"), _unit(sku="C")])
    model.remove_rows_at([0, 2])
    assert model.rowCount() == 1
    assert model.load_units()[0].sku == "B"


def test_set_data_updates_sku_via_replace(qapp: QApplication) -> None:
    model = ProductTableModel([_unit(sku="OLD")])
    index = model.index(0, COL_SKU)
    ok = model.setData(index, "NEW", Qt.ItemDataRole.EditRole)
    assert ok is True
    assert model.load_units()[0].sku == "NEW"


def test_set_data_rejects_invalid_domain_value(qapp: QApplication) -> None:
    model = ProductTableModel([_unit(sku="KEEP")])
    index = model.index(0, COL_SKU)
    ok = model.setData(index, "   ", Qt.ItemDataRole.EditRole)  # SKU vacío -> DomainValidationError
    assert ok is False
    assert model.load_units()[0].sku == "KEEP"


def test_toggling_fragile_checkbox_updates_unit(qapp: QApplication) -> None:
    model = ProductTableModel([_unit()])
    index = model.index(0, COL_FRAGILE)
    assert model.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked

    model.setData(index, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
    assert model.load_units()[0].fragile is True
    assert model.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked


def test_toggling_extinguisher_checkbox_keeps_domain_invariants(qapp: QApplication) -> None:
    model = ProductTableModel([_unit()])
    index = model.index(0, COL_EXTINGUISHER)

    model.setData(index, Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole)
    unit = model.load_units()[0]
    assert unit.is_extinguisher is True
    assert unit.extinguisher_nominal_kg is not None

    model.setData(index, Qt.CheckState.Unchecked.value, Qt.ItemDataRole.CheckStateRole)
    unit = model.load_units()[0]
    assert unit.is_extinguisher is False
    assert unit.extinguisher_nominal_kg is None


def test_invalid_index_returns_none_and_rejects_writes(qapp: QApplication) -> None:
    model = ProductTableModel([_unit()])
    invalid = QModelIndex()
    assert model.data(invalid) is None
    assert model.setData(invalid, "x") is False


def test_flags_mark_sku_editable_and_orientations_read_only(qapp: QApplication) -> None:
    model = ProductTableModel([_unit()])
    from cargo_optimizer.presentation.desktop.models.product_table_model import COL_ORIENTATIONS

    sku_flags = model.flags(model.index(0, COL_SKU))
    orientations_flags = model.flags(model.index(0, COL_ORIENTATIONS))

    assert sku_flags & Qt.ItemFlag.ItemIsEditable
    assert not (orientations_flags & Qt.ItemFlag.ItemIsEditable)
