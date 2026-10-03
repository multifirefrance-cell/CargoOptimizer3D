"""`LoadingSpaceEditorDialog`: envoltorio delgado sobre `LoadingSpaceFormPanel`.

Reutiliza `LoadingSpaceFormPanel` tal cual (mismos campos, mismo
bloqueo de perfil/"Personalizado") para editar el `LoadingSpace` del
proyecto **actual** — a diferencia de `LoadingSpaceProfileEditorDialog`
(que crea/edita una fila del catálogo de perfiles en SQLite), este
diálogo no escribe nada en el catálogo: solo expone el formulario
completo bajo demanda ("Cambiar medidas…" en
`LoadingSpaceSummaryPanel`), en vez de mantenerlo siempre visible en la
columna izquierda (rediseño UX: "workspace operativo").
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QScrollArea, QVBoxLayout, QWidget

from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    LoadingSpaceFormPanel,
)


class LoadingSpaceEditorDialog(QDialog):
    """Diálogo modal: el formulario completo de espacio de carga, para uso ocasional."""

    def __init__(self, parent: QWidget | None, *, form_panel: LoadingSpaceFormPanel) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cambiar medidas del espacio de carga")
        self.resize(480, 560)
        self.form_panel = form_panel

        # Un único botón "Cerrar": los campos ya son la fuente de verdad en
        # vivo (igual que cuando el formulario estaba siempre embebido),
        # así que no hay "Aceptar/Cancelar" que distinga un estado
        # confirmado de uno descartado.
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        button_box.rejected.connect(self.accept)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.form_panel)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(button_box)
