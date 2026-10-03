"""`LoadingSpaceProfileEditorDialog`: editor modal de un perfil de espacio (fase 7.1).

Reutiliza `LoadingSpaceFormPanel` tal cual (mismos campos, mismo
bloqueo de perfil/"Personalizado") en vez de duplicar un formulario de
`LoadingSpace` nuevo — "no crear un editor gigante nuevo si puede
reutilizarse lógica existente" (encargo de la fase 7.1, sección 19,
aplicado aquí igual que al catálogo).
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    PROFILE_CUSTOM,
    LoadingSpaceFormPanel,
)


class LoadingSpaceProfileEditorDialog(QDialog):
    """Formulario modal para crear o editar un perfil de espacio, sobre `LoadingSpaceFormPanel`."""

    def __init__(self, parent: QWidget | None = None, *, space: LoadingSpace | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Editar perfil de espacio" if space is not None else "Nuevo perfil de espacio"
        )
        self.resize(480, 560)
        self._result_space: LoadingSpace | None = None

        self.form_panel = LoadingSpaceFormPanel(self)
        if space is not None:
            self.form_panel.set_loading_space(space)
        else:
            self.form_panel.set_current_profile_name(PROFILE_CUSTOM)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setProperty("class", "primary")

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.form_panel)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._button_box)

    def _on_accept(self) -> None:
        space = self.form_panel.build_loading_space()
        if space is None:
            QMessageBox.warning(
                self,
                "Datos inválidos",
                "Define un espacio de carga válido (nombre, dimensiones positivas y, si "
                "aplica, un peso máximo positivo).",
            )
            return
        self._result_space = space
        self.accept()

    def result_space(self) -> LoadingSpace | None:
        """El `LoadingSpace` construido y válido tras aceptar, o `None` si se canceló."""
        return self._result_space
