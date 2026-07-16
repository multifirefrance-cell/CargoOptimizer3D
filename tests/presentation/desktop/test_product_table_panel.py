"""Pruebas de `ProductTablePanel`: alta/edición de productos vía diálogo dedicado.

Nunca se llama a `.exec()` de verdad (bloquearía el hilo esperando un
clic bajo `offscreen`): `CatalogProductEditorDialog` se sustituye por un
doble de prueba que simula Aceptar/Cancelar sin entrar en un bucle
modal real — mismo patrón que `test_product_catalog_dialog.py`.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication, QDialog

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.panels import product_table_panel as panel_module
from cargo_optimizer.presentation.desktop.panels.product_table_panel import ProductTablePanel


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def _fake_editor_dialog_class(accepted: bool, result_unit: LoadUnit | None) -> type:
    class _FakeEditorDialog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected

        def result_load_unit(self) -> LoadUnit | None:
            return result_unit

    return _FakeEditorDialog


def test_on_add_product_opens_dialog_and_appends_result(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    monkeypatch.setattr(
        panel_module,
        "CatalogProductEditorDialog",
        _fake_editor_dialog_class(True, _unit(sku="NEW-1")),
    )

    panel._on_add_product()

    assert panel.model.rowCount() == 1
    assert panel.model.load_units()[0].sku == "NEW-1"


def test_on_add_product_cancelled_adds_nothing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    monkeypatch.setattr(
        panel_module, "CatalogProductEditorDialog", _fake_editor_dialog_class(False, None)
    )

    panel._on_add_product()

    assert panel.model.rowCount() == 0


def test_on_edit_selected_product_replaces_the_row(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.model.add_units((_unit(sku="OLD"),))
    panel.table_view.selectRow(0)
    monkeypatch.setattr(
        panel_module,
        "CatalogProductEditorDialog",
        _fake_editor_dialog_class(True, _unit(sku="OLD", name="Actualizado")),
    )

    panel._on_edit_selected_product()

    assert panel.model.load_units()[0].name == "Actualizado"


def test_on_edit_without_selection_does_nothing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.model.add_units((_unit(sku="OLD"),))
    called = []
    monkeypatch.setattr(
        panel_module, "CatalogProductEditorDialog", lambda *a, **k: called.append(1)
    )

    panel._on_edit_selected_product()

    assert called == []


def test_double_click_opens_editor_for_that_row(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.model.add_units((_unit(sku="A"), _unit(sku="B")))
    monkeypatch.setattr(
        panel_module,
        "CatalogProductEditorDialog",
        _fake_editor_dialog_class(True, _unit(sku="B", name="Editado por doble clic")),
    )

    panel._on_row_double_clicked(panel.model.index(1, 0))

    assert panel.model.load_units()[1].name == "Editado por doble clic"


def test_double_click_on_invalid_index_does_nothing(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = ProductTablePanel()
    panel.model.add_units((_unit(sku="A"),))
    called = []
    monkeypatch.setattr(
        panel_module, "CatalogProductEditorDialog", lambda *a, **k: called.append(1)
    )

    panel._on_row_double_clicked(QModelIndex())

    assert called == []
