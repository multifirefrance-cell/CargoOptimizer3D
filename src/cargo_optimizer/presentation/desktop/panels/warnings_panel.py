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
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

_NO_WARNINGS_MESSAGE = "Sin avisos."
_WARNING_BG = QColor("#FFF8E1")       # ámbar muy claro (tema claro)
_WARNING_FG = QColor("#7A4F00")       # ámbar oscuro para texto legible sobre fondo claro
_WARNING_BG_DARK = QColor("#2A2010")  # ámbar oscuro sutil (tema oscuro)
_WARNING_FG_DARK = QColor("#F2A93B")  # ámbar claro sobre fondo oscuro


class WarningsPanel(QWidget):
    """Lista de avisos de la última ejecución del motor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("warningsPanel")
        self._dark: bool = False

        self._list = QListWidget(self)
        self._list.setObjectName("warningsList")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self.clear()

    def set_dark_mode(self, dark: bool) -> None:
        self._dark = dark

    def set_warnings(self, warnings: Sequence[str]) -> None:
        self._list.clear()
        if not warnings:
            placeholder = QListWidgetItem(_NO_WARNINGS_MESSAGE)
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(placeholder)
            return
        bg = _WARNING_BG_DARK if self._dark else _WARNING_BG
        fg = _WARNING_FG_DARK if self._dark else _WARNING_FG
        for warning in warnings:
            item = QListWidgetItem(f"⚠  {warning}")
            item.setBackground(bg)
            item.setForeground(fg)
            self._list.addItem(item)

    def clear(self) -> None:
        self.set_warnings(())
