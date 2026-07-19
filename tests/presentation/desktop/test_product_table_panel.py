"""Pruebas de `ProductTablePanel`: "Lista de carga" simplificada + relay de alta rápida.

Rediseño "workspace operativo": alta y edición de cantidad ya no abren
`CatalogProductEditorDialog` desde este panel — ese diálogo solo se usa
para "Crear nuevo SKU…" dentro de `ProductQuickAddPanel` (probado por
separado en `test_product_quick_add_panel.py`). Aquí se prueba: el
relay de `add_requested`, `add_units_to_load`, "Editar cantidad…" (vía
`QInputDialog` sustituido por un doble), "Eliminar", el estado vacío
(`QStackedWidget`) y que las columnas técnicas del catálogo permanezcan
ocultas.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.models.product_table_model import (
    COL_COLOR,
    COL_NAME,
    COL_QUANTITY,
    COL_SKU,
    COL_WEIGHT_TOTAL,
)
from cargo_optimizer.presentation.desktop.panels import product_table_panel as panel_module
from cargo_optimizer.presentation.desktop.panels.product_table_panel import (
    _PAGE_EMPTY,
    _PAGE_TABLE,
    ProductTablePanel,
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


def test_starts_on_empty_page(qapp: QApplication) -> None:
    panel = ProductTablePanel()
    assert panel._stack.currentIndex() == _PAGE_EMPTY


def test_add_units_to_load_switches_to_table_page(qapp: QApplication) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"),))
    assert panel._stack.currentIndex() == _PAGE_TABLE
    assert panel.model.rowCount() == 1


def test_removing_last_row_returns_to_empty_page(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"),))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )
    panel.remove_selected_rows()
    assert panel._stack.currentIndex() == _PAGE_EMPTY
    assert panel.model.rowCount() == 0


def test_only_load_relevant_columns_are_visible(qapp: QApplication) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"),))
    for column in (COL_SKU, COL_NAME, COL_QUANTITY, COL_WEIGHT_TOTAL):
        assert not panel.table_view.isColumnHidden(column)
    assert panel.table_view.isColumnHidden(COL_COLOR)


def test_quick_add_panel_add_requested_is_relayed(qapp: QApplication) -> None:
    panel = ProductTablePanel()
    received: list[tuple[object, int]] = []
    panel.add_requested.connect(lambda unit, qty: received.append((unit, qty)))
    catalog_unit = _unit(sku="CAT-1")

    panel.quick_add_panel.add_requested.emit(catalog_unit, 7)

    assert received == [(catalog_unit, 7)]


def test_edit_quantity_updates_the_row(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A", quantity=1),))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        panel_module.QInputDialog, "getInt", staticmethod(lambda *a, **k: (5, True))
    )

    panel._on_edit_quantity_clicked()

    assert panel.model.load_units()[0].quantity == 5


def test_edit_quantity_cancelled_leaves_row_unchanged(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A", quantity=1),))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        panel_module.QInputDialog, "getInt", staticmethod(lambda *a, **k: (5, False))
    )

    panel._on_edit_quantity_clicked()

    assert panel.model.load_units()[0].quantity == 1


def test_edit_quantity_without_selection_does_nothing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A", quantity=1),))
    called = []
    monkeypatch.setattr(
        panel_module.QInputDialog, "getInt", staticmethod(lambda *a, **k: called.append(1))
    )

    panel._on_edit_quantity_clicked()

    assert called == []


def test_remove_selected_rows_deletes_the_row(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"), _unit(sku="B")))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    panel.remove_selected_rows()

    assert panel.model.rowCount() == 1
    assert panel.model.load_units()[0].sku == "B"


def test_remove_selected_rows_asks_for_confirmation_first(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"),))
    panel.table_view.selectRow(0)
    asked: list[tuple[object, ...]] = []

    def _fake_question(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        asked.append(args)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake_question))

    panel.remove_selected_rows()

    assert len(asked) == 1
    assert panel.model.rowCount() == 0


def test_remove_selected_rows_declined_leaves_row_intact(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.add_units_to_load((_unit(sku="A"),))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    )

    panel.remove_selected_rows()

    assert panel.model.rowCount() == 1
    assert panel.model.load_units()[0].sku == "A"


def test_set_catalog_repository_propagates_to_quick_add_panel(qapp: QApplication) -> None:
    panel = ProductTablePanel()
    panel.set_catalog_repository(None)
    assert panel.quick_add_panel._repository is None
