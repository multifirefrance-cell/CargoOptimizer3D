"""Pruebas de `ProductQuickAddPanel` contra un catálogo SQLite real (temporal).

"Crear nuevo SKU…" abre `CatalogProductEditorDialog`: nunca se llama a
`.exec()` real (bloquearía el hilo bajo `offscreen`), se sustituye por
un doble de prueba — mismo patrón que `test_product_catalog_dialog.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.panels import product_quick_add_panel as panel_module
from cargo_optimizer.presentation.desktop.panels.product_quick_add_panel import (
    ProductQuickAddPanel,
)


def _repository(tmp_path: Path) -> ProductCatalogRepository:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return ProductCatalogRepository(manager)


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja de herramientas",
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


def test_search_by_sku_resolves_the_product(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    panel = ProductQuickAddPanel(repository=repo)

    panel._search_edit.setText("BOX-1")

    assert panel._resolved_unit is not None
    assert panel._resolved_unit.sku == "BOX-1"
    assert panel._add_button.isEnabled()


def test_search_by_display_name_resolves_the_product(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1", name="Caja de herramientas"))
    panel = ProductQuickAddPanel(repository=repo)

    panel._search_edit.setText("BOX-1 — Caja de herramientas")

    assert panel._resolved_unit is not None
    assert panel._resolved_unit.sku == "BOX-1"


def test_unresolved_text_disables_add_button(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    panel = ProductQuickAddPanel(repository=repo)

    panel._search_edit.setText("no existe")

    assert panel._resolved_unit is None
    assert not panel._add_button.isEnabled()


def test_add_clicked_emits_add_requested_with_quantity(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    panel = ProductQuickAddPanel(repository=repo)
    panel._search_edit.setText("BOX-1")
    panel._quantity_spin.setValue(12)
    received: list[tuple[LoadUnit, int]] = []
    panel.add_requested.connect(lambda unit, qty: received.append((unit, qty)))

    panel._on_add_clicked()

    assert len(received) == 1
    unit, quantity = received[0]
    assert unit.sku == "BOX-1"
    assert quantity == 12


def test_add_clicked_clears_search_and_resets_quantity(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    panel = ProductQuickAddPanel(repository=repo)
    panel._search_edit.setText("BOX-1")
    panel._quantity_spin.setValue(5)

    panel._on_add_clicked()

    assert panel._search_edit.text() == ""
    assert panel._quantity_spin.value() == 1


def test_add_clicked_without_resolved_unit_does_nothing(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    panel = ProductQuickAddPanel(repository=repo)
    received: list[object] = []
    panel.add_requested.connect(lambda unit, qty: received.append((unit, qty)))

    panel._on_add_clicked()

    assert received == []


def test_no_repository_disables_search_and_create(qapp: QApplication) -> None:
    panel = ProductQuickAddPanel(repository=None)

    assert not panel._search_edit.isEnabled()
    assert not panel._create_sku_button.isEnabled()


def test_set_repository_refreshes_catalog(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    panel = ProductQuickAddPanel(repository=None)

    panel.set_repository(repo)
    repo.add(_unit(sku="BOX-1"))
    panel.refresh_catalog()

    assert panel._search_edit.isEnabled()
    panel._search_edit.setText("BOX-1")
    assert panel._resolved_unit is not None


def test_create_new_sku_adds_to_catalog_and_selects_it(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    panel = ProductQuickAddPanel(repository=repo)
    monkeypatch.setattr(
        panel_module,
        "CatalogProductEditorDialog",
        _fake_editor_dialog_class(True, _unit(sku="NEW-1", name="Producto nuevo")),
    )

    panel._on_create_new_sku()

    assert repo.get_by_sku("NEW-1") is not None
    assert panel._search_edit.text() == "NEW-1 — Producto nuevo"
    assert panel._resolved_unit is not None
    assert panel._resolved_unit.sku == "NEW-1"


def test_create_new_sku_cancelled_adds_nothing(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    panel = ProductQuickAddPanel(repository=repo)
    monkeypatch.setattr(
        panel_module, "CatalogProductEditorDialog", _fake_editor_dialog_class(False, None)
    )

    panel._on_create_new_sku()

    assert repo.get_by_sku("NEW-1") is None
    assert panel._search_edit.text() == ""


def test_catalog_technical_fields_are_preserved_on_the_resolved_unit(
    qapp: QApplication, tmp_path: Path
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1", fragile=True, max_stack_count=2))
    panel = ProductQuickAddPanel(repository=repo)

    panel._search_edit.setText("BOX-1")

    assert panel._resolved_unit is not None
    assert panel._resolved_unit.fragile is True
    assert panel._resolved_unit.max_stack_count == 2
