"""Pruebas de `ProductCatalogDialog` contra un catálogo SQLite real (temporal).

Nunca se llama a `.exec()` de verdad (bloquearía el hilo esperando un
clic bajo `offscreen`, ver `docs/Database.md`): los flujos que abren un
diálogo hijo (`CatalogProductEditorDialog`) sustituyen esa clase por un
doble de prueba que simula Aceptar/Cancelar sin entrar en un bucle
modal real.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.dialogs import product_catalog_dialog as dialog_module
from cargo_optimizer.presentation.desktop.dialogs.product_catalog_dialog import (
    ProductCatalogDialog,
)


def _repository(tmp_path: Path) -> ProductCatalogRepository:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return ProductCatalogRepository(manager)


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


def test_dialog_shows_only_active_products_by_default(qapp: QApplication, tmp_path: Path) -> None:
    # Corrección UX archivar/eliminar: por defecto solo se ven los SKU
    # activos -- antes de esta corrección, un SKU archivado se mostraba
    # mezclado con los activos sin ningún filtro ni distinción clara.
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1"))
    repo.add(_unit(sku="BOX-2"))
    repo.archive(added.id)

    dialog = ProductCatalogDialog(None, repository=repo)

    assert dialog.model.rowCount() == 1
    assert dialog.model.entry_at(0).load_unit.sku == "BOX-2"


def test_show_archived_checkbox_reveals_archived_products(
    qapp: QApplication, tmp_path: Path
) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1"))
    repo.add(_unit(sku="BOX-2"))
    repo.archive(added.id)

    dialog = ProductCatalogDialog(None, repository=repo)
    assert dialog.model.rowCount() == 1

    dialog._show_archived_check.setChecked(True)

    assert dialog.model.rowCount() == 2
    skus = {dialog.model.entry_at(row).load_unit.sku for row in range(dialog.model.rowCount())}
    assert skus == {"BOX-1", "BOX-2"}

    dialog._show_archived_check.setChecked(False)

    assert dialog.model.rowCount() == 1


def test_show_archived_checkbox_distinguishes_active_from_archived(
    qapp: QApplication, tmp_path: Path
) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1"))
    repo.add(_unit(sku="BOX-2"))
    repo.archive(added.id)

    dialog = ProductCatalogDialog(None, repository=repo)
    dialog._show_archived_check.setChecked(True)

    entries_by_sku = {
        dialog.model.entry_at(row).load_unit.sku: dialog.model.entry_at(row).is_active
        for row in range(dialog.model.rowCount())
    }
    assert entries_by_sku == {"BOX-1": False, "BOX-2": True}


def test_search_with_archived_shown_filters_by_text_too(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1", name="Caja de herramientas"))
    repo.add(_unit(sku="PALLET-1", name="Pallet"))
    repo.archive(added.id)

    dialog = ProductCatalogDialog(None, repository=repo)
    dialog._show_archived_check.setChecked(True)
    dialog._search_edit.setText("herramientas")

    assert dialog.model.rowCount() == 1
    assert dialog.model.entry_at(0).load_unit.sku == "BOX-1"


def test_archive_button_is_labeled_archivar_not_eliminar(
    qapp: QApplication, tmp_path: Path
) -> None:
    # No debe existir ninguna acción rotulada "Eliminar" que en realidad
    # solo archive -- corrección UX explícita pedida por el usuario.
    repo = _repository(tmp_path)
    dialog = ProductCatalogDialog(None, repository=repo)

    assert dialog._archive_button.text() == "Archivar"
    assert "eliminar" not in dialog._archive_button.text().lower()
    all_button_texts = " ".join(
        button.text().lower()
        for button in (
            dialog._add_button,
            dialog._edit_button,
            dialog._duplicate_button,
            dialog._archive_button,
            dialog._restore_button,
        )
    )
    assert "eliminar" not in all_button_texts


def test_search_filters_to_active_matches(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1", name="Caja de herramientas"))
    repo.add(_unit(sku="PALLET-1", name="Pallet"))

    dialog = ProductCatalogDialog(None, repository=repo)
    dialog._search_edit.setText("herramientas")

    assert dialog.model.rowCount() == 1
    assert dialog.model.entry_at(0).load_unit.sku == "BOX-1"


def test_on_add_creates_a_new_catalog_product(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = ProductCatalogDialog(None, repository=repo)
    monkeypatch.setattr(
        dialog_module,
        "CatalogProductEditorDialog",
        _fake_editor_dialog_class(True, _unit(sku="NEW-1")),
    )

    dialog._on_add()

    assert repo.get_by_sku("NEW-1") is not None
    assert dialog.model.rowCount() == 1


def test_on_add_cancelled_does_not_create_a_product(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = ProductCatalogDialog(None, repository=repo)
    monkeypatch.setattr(
        dialog_module, "CatalogProductEditorDialog", _fake_editor_dialog_class(False, None)
    )

    dialog._on_add()

    assert repo.count_active() == 0


def test_on_edit_updates_the_selected_product(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1", name="Original"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    updated_unit = LoadUnit(
        id=added.id, sku="BOX-1", name="Actualizado", dimensions=added.dimensions, weight_kg=99.0
    )
    monkeypatch.setattr(
        dialog_module, "CatalogProductEditorDialog", _fake_editor_dialog_class(True, updated_unit)
    )

    dialog._on_edit()

    assert repo.get_by_id(added.id).name == "Actualizado"  # type: ignore[union-attr]


def test_double_click_opens_the_same_editor_as_edit_button(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_unit(sku="BOX-1", name="Original"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    updated_unit = LoadUnit(
        id=added.id,
        sku="BOX-1",
        name="Editado por doble clic",
        dimensions=added.dimensions,
        weight_kg=99.0,
    )
    monkeypatch.setattr(
        dialog_module, "CatalogProductEditorDialog", _fake_editor_dialog_class(True, updated_unit)
    )

    dialog._on_row_double_clicked(dialog.model.index(0, 0))

    assert repo.get_by_id(added.id).name == "Editado por doble clic"  # type: ignore[union-attr]


def test_single_click_selection_does_not_open_the_editor(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    opened: list[object] = []
    monkeypatch.setattr(
        dialog_module,
        "CatalogProductEditorDialog",
        lambda *a, **k: opened.append((a, k)) or _fake_editor_dialog_class(False, None)(*a, **k),
    )

    dialog.table_view.selectRow(0)

    assert dialog._selected_row() == 0
    assert opened == []


def test_double_click_on_invalid_index_does_nothing(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    opened: list[object] = []
    monkeypatch.setattr(
        dialog_module,
        "CatalogProductEditorDialog",
        lambda *a, **k: opened.append((a, k)) or _fake_editor_dialog_class(False, None)(*a, **k),
    )

    dialog._on_row_double_clicked(QModelIndex())

    assert opened == []


def test_on_duplicate_prompts_for_new_sku(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("BOX-2", True)))

    dialog._on_duplicate()

    assert repo.get_by_sku("BOX-2") is not None
    assert repo.count_active() == 2


def test_on_archive_then_restore(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    )

    dialog._on_archive()
    assert repo.count_active() == 0
    # Con el filtro por defecto (solo activos), el SKU recién archivado
    # ya no aparece en la lista -- hay que pedir explícitamente verlo
    # para poder seleccionarlo y restaurarlo, igual que haría un usuario
    # real.
    assert dialog.model.rowCount() == 0
    dialog._show_archived_check.setChecked(True)
    assert dialog.model.rowCount() == 1

    dialog.table_view.selectRow(0)
    dialog._on_restore()
    assert repo.count_active() == 1


def test_on_archive_asks_for_confirmation_first(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    asked: list[tuple[object, ...]] = []

    def _fake_question(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        asked.append(args)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake_question))

    dialog._on_archive()

    assert len(asked) == 1
    assert repo.count_active() == 0


def test_on_archive_declined_leaves_product_active(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    )

    dialog._on_archive()

    assert repo.count_active() == 1


def test_on_add_to_project_without_selection_shows_information(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = ProductCatalogDialog(None, repository=repo)
    infos: list[tuple[object, ...]] = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: infos.append(a)))

    dialog._on_add_to_project()

    assert dialog.selected_units_to_add() == ()
    assert len(infos) == 1


def test_on_add_to_project_with_selection_returns_units_and_accepts(
    qapp: QApplication, tmp_path: Path
) -> None:
    repo = _repository(tmp_path)
    repo.add(_unit(sku="BOX-1"))
    dialog = ProductCatalogDialog(None, repository=repo)
    dialog.table_view.selectRow(0)

    dialog._on_add_to_project()

    units = dialog.selected_units_to_add()
    assert len(units) == 1
    assert units[0].sku == "BOX-1"
