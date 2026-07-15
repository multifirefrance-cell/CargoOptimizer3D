"""Placeholder de la vista 3D — sin VTK todavía (llega en la fase 6).

Un `QWidget` sencillo que ocupa correctamente el espacio de la zona
central y comunica con claridad que la vista real no existe aún, en vez
de dejar un hueco vacío o silencioso.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class Viewport3DPlaceholder(QWidget):
    """Ocupa el lugar de la futura vista 3D (VTK, fase 6)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("viewport3dPlaceholder")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(True)

        icon_label = QLabel("⬚", self)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = icon_label.font()
        icon_font.setPointSize(icon_font.pointSize() + 24)
        icon_label.setFont(icon_font)

        message_label = QLabel("Vista 3D disponible en la Fase 6", self)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_font = message_label.font()
        message_font.setItalic(True)
        message_label.setFont(message_font)

        for label in (icon_label, message_label):
            label.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(icon_label)
        layout.addWidget(message_label)
        layout.addStretch(1)
