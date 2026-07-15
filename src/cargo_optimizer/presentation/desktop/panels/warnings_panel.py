"""Panel de avisos de la última ejecución (`PackingResult.warnings`).

`PackingResult.warnings` ya agrega, como texto plano, cualquier aviso
generado durante el empaquetado (de `RuleEvaluation`, del propio bucle
de la estrategia, o del `progress_callback` del usuario si fallara) —
ver `docs/OptimizationEngine.md`. Este panel no distingue su origen
porque el motor tampoco lo hace: son todos "avisos de la ejecución".
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

_NO_WARNINGS_MESSAGE = "Sin avisos."


class WarningsPanel(QWidget):
    """Lista de avisos de la última ejecución del motor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("warningsPanel")

        self._list = QListWidget(self)
        self._list.setObjectName("warningsList")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self.clear()

    def set_warnings(self, warnings: Sequence[str]) -> None:
        self._list.clear()
        if not warnings:
            placeholder = QListWidgetItem(_NO_WARNINGS_MESSAGE)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(placeholder)
            return
        for warning in warnings:
            self._list.addItem(QListWidgetItem(warning))

    def clear(self) -> None:
        self.set_warnings(())
