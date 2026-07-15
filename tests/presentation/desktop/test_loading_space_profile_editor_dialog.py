"""Pruebas de `LoadingSpaceProfileEditorDialog`, sin llamar a `exec()`."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.dialogs.loading_space_profile_editor_dialog import (
    LoadingSpaceProfileEditorDialog,
)
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import PROFILE_CUSTOM


def test_new_dialog_starts_in_custom_mode(qapp: QApplication) -> None:
    dialog = LoadingSpaceProfileEditorDialog(None)
    assert dialog.form_panel.current_profile_name() == PROFILE_CUSTOM


def test_editing_populates_form_from_space(qapp: QApplication) -> None:
    space = LoadingSpace(
        name="Bodega X",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
        door_position=DoorPosition.UNRESTRICTED,
        max_weight_kg=None,
        notes="Notas",
    )
    dialog = LoadingSpaceProfileEditorDialog(None, space=space)
    built = dialog.form_panel.build_loading_space()
    assert built is not None
    assert built.name == "Bodega X"
    assert built.notes == "Notas"


def test_accepting_with_valid_data_sets_result(qapp: QApplication) -> None:
    dialog = LoadingSpaceProfileEditorDialog(None)
    dialog.form_panel._name_edit.setText("Perfil nuevo")

    dialog._on_accept()

    result = dialog.result_space()
    assert result is not None
    assert result.name == "Perfil nuevo"


def test_accepting_with_empty_name_shows_warning_and_does_not_accept(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *args, **_kwargs: warnings.append(args)),
    )
    dialog = LoadingSpaceProfileEditorDialog(None)
    dialog.form_panel._name_edit.setText("")

    dialog._on_accept()

    assert dialog.result_space() is None
    assert len(warnings) == 1
