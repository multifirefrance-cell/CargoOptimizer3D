"""Pruebas de `ColumnMappingDialog`: detección preseleccionada, edición manual, perfiles (8.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import ImportMappingProfileRepository
from cargo_optimizer.presentation.desktop.dialogs.column_mapping_dialog import ColumnMappingDialog


def _repository(tmp_path: Path) -> ImportMappingProfileRepository:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return ImportMappingProfileRepository(manager)


def test_dialog_preselects_detected_mapping(qapp: QApplication) -> None:
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Código", "Almacen"),
        detected_mapping={"Código": "SKU"},
    )

    assert dialog._combos[0].currentText() == "SKU"
    assert dialog._combos[1].currentText() == "(Ignorar)"


def test_accept_returns_current_mapping_excluding_ignored(qapp: QApplication) -> None:
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Código", "Almacen"),
        detected_mapping={"Código": "SKU"},
    )

    dialog._on_accept()

    assert dialog.result_mapping() == {"Código": "SKU"}


def test_manual_reassignment_of_unrecognized_column(qapp: QApplication) -> None:
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Código", "Almacen"),
        detected_mapping={"Código": "SKU"},
    )

    dialog._combos[1].setCurrentText("Notas")
    dialog._on_accept()

    assert dialog.result_mapping() == {"Código": "SKU", "Almacen": "Notas"}


def test_cancel_leaves_result_mapping_as_none(qapp: QApplication) -> None:
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Código",),
        detected_mapping={"Código": "SKU"},
    )

    dialog.reject()

    assert dialog.result_mapping() is None


def test_save_as_profile_persists_current_mapping(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Código", "Descripción"),
        detected_mapping={"Código": "SKU", "Descripción": "Nombre"},
        profile_repository=repo,
    )
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Mi perfil", True)))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))

    dialog._on_save_profile()

    saved = repo.get_by_name("Mi perfil")
    assert saved is not None
    assert saved.column_mapping == {"Código": "SKU", "Descripción": "Nombre"}


def test_choosing_saved_profile_applies_its_mapping(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    profile = repo.add("Kupfer-como", "catalog", {"Ref": "SKU", "Descripcion": "Nombre"})
    dialog = ColumnMappingDialog(
        None,
        target_kind="catalog",
        source_headers=("Ref", "Descripcion"),
        detected_mapping={},
        profile_repository=repo,
    )
    combo = dialog._load_profile_combo
    index = next(i for i in range(combo.count()) if combo.itemData(i) == profile.id)

    combo.setCurrentIndex(index)

    assert dialog._combos[0].currentText() == "SKU"
    assert dialog._combos[1].currentText() == "Nombre"
    refreshed = repo.get_by_id(profile.id)
    assert refreshed is not None
    assert refreshed.last_used_at is not None
