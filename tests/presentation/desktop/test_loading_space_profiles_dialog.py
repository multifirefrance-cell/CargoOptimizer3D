"""Pruebas de `LoadingSpaceProfilesDialog` contra un catálogo SQLite real (temporal).

Igual que `test_product_catalog_dialog.py`: nunca se llama a `.exec()`
de verdad; el diálogo hijo de edición se sustituye por un doble simple.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import LoadingSpaceProfileRepository
from cargo_optimizer.presentation.desktop.dialogs import (
    loading_space_profiles_dialog as dialog_module,
)
from cargo_optimizer.presentation.desktop.dialogs.loading_space_profiles_dialog import (
    LoadingSpaceProfilesDialog,
)


def _repository(tmp_path: Path) -> LoadingSpaceProfileRepository:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return LoadingSpaceProfileRepository(manager)


def _space(**overrides: object) -> LoadingSpace:
    kwargs: dict[str, object] = {
        "name": "Bodega",
        "category": LoadingSpaceCategory.WAREHOUSE,
        "internal_dimensions": Dimensions3D(500.0, 300.0, 300.0),
    }
    kwargs.update(overrides)
    return LoadingSpace(**kwargs)  # type: ignore[arg-type]


def _fake_editor_dialog_class(accepted: bool, result_space: LoadingSpace | None) -> type:
    class _FakeEditorDialog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def exec(self) -> QDialog.DialogCode:
            return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected

        def result_space(self) -> LoadingSpace | None:
            return result_space

    return _FakeEditorDialog


def test_dialog_lists_builtin_and_custom_profiles(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.ensure_builtin_profiles()
    repo.add(_space(name="Personalizado"))

    dialog = LoadingSpaceProfilesDialog(None, repository=repo)

    assert dialog.model.rowCount() == 4


def test_search_filters_by_name(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_space(name="Camión rígido"))
    repo.add(_space(name="Semirremolque"))

    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog._search_edit.setText("camión")

    assert dialog.model.rowCount() == 1


def test_on_add_creates_a_new_profile(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    monkeypatch.setattr(
        dialog_module,
        "LoadingSpaceProfileEditorDialog",
        _fake_editor_dialog_class(True, _space(name="Nuevo perfil")),
    )

    dialog._on_add()

    assert repo.get_by_name("Nuevo perfil") is not None


def test_on_edit_builtin_profile_shows_information_and_does_not_open_editor(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.ensure_builtin_profiles()
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    infos: list[tuple[object, ...]] = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: infos.append(a)))

    dialog._on_edit()

    assert len(infos) == 1


def test_on_edit_custom_profile_updates_it(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_space(name="Original"))
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    updated = LoadingSpace(
        id=added.id,
        name="Original",
        category=added.category,
        internal_dimensions=Dimensions3D(999.0, 300.0, 300.0),
    )
    monkeypatch.setattr(
        dialog_module, "LoadingSpaceProfileEditorDialog", _fake_editor_dialog_class(True, updated)
    )

    dialog._on_edit()

    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.internal_dimensions.length_cm == 999.0


def test_on_duplicate_prompts_for_new_name(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    repo.add(_space(name="Original"))
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog.table_view.selectRow(0)
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Copia", True)))

    dialog._on_duplicate()

    assert repo.get_by_name("Copia") is not None


def test_on_archive_then_restore(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    added = repo.add(_space(name="Perfil"))
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog.table_view.selectRow(0)

    dialog._on_archive()
    assert repo.get_by_name("Perfil") is None

    dialog.table_view.selectRow(0)
    dialog._on_restore()
    assert repo.get_by_name("Perfil") is not None
    assert repo.get_by_id(added.id) is not None


def test_on_apply_without_selection_shows_information(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repository(tmp_path)
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    infos: list[tuple[object, ...]] = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: infos.append(a)))

    dialog._on_apply()

    assert dialog.result_space() is None
    assert len(infos) == 1


def test_on_apply_with_selection_returns_the_space(qapp: QApplication, tmp_path: Path) -> None:
    repo = _repository(tmp_path)
    repo.add(_space(name="Perfil elegido"))
    dialog = LoadingSpaceProfilesDialog(None, repository=repo)
    dialog.table_view.selectRow(0)

    dialog._on_apply()

    result = dialog.result_space()
    assert result is not None
    assert result.name == "Perfil elegido"
