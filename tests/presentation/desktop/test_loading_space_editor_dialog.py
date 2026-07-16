"""Pruebas de `LoadingSpaceEditorDialog`: envoltorio de diálogo sobre `LoadingSpaceFormPanel` real.

Nunca se llama a `.exec()` (bloquearía el hilo bajo `offscreen`): solo
se comprueba que el diálogo reutiliza la misma instancia de
`LoadingSpaceFormPanel` (nunca una copia) y que "Cerrar" acepta el
diálogo sin descartar el estado del formulario.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from cargo_optimizer.presentation.desktop.dialogs.loading_space_editor_dialog import (
    LoadingSpaceEditorDialog,
)
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    LoadingSpaceFormPanel,
)


def test_dialog_embeds_the_same_form_panel_instance(qapp: QApplication) -> None:
    form_panel = LoadingSpaceFormPanel()
    dialog = LoadingSpaceEditorDialog(None, form_panel=form_panel)
    assert dialog.form_panel is form_panel


def test_close_button_accepts_the_dialog(qapp: QApplication) -> None:
    form_panel = LoadingSpaceFormPanel()
    dialog = LoadingSpaceEditorDialog(None, form_panel=form_panel)
    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    close_button = button_box.button(QDialogButtonBox.StandardButton.Close)
    assert close_button is not None

    close_button.click()

    assert dialog.result() == dialog.DialogCode.Accepted
