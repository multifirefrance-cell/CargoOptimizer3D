"""Panel de registro: inicio, fin, duración, errores y cancelación de cada ejecución.

Registro puramente informativo de esta sesión de la interfaz: se
descarta deliberadamente al cerrar la ventana. No es un descuido — ni
`.cargo3d` (fase 7.0) ni `project_history`/`packing_run_history`
(catálogo SQLite, fase 7.1) guardan esta bitácora entrada por entrada,
solo metadatos agregados (ver `docs/Database.md`); "qué pasó en esta
ventana abierta" es un registro efímero, no un historial de proyecto.
Usa la fuente de ancho fijo del sistema
(`QFontDatabase.SystemFont.FixedFont`) para que las marcas de tiempo
alineen, sin fijar un nombre de fuente concreto que pueda no estar
instalado.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.presentation.desktop.style import (
    ERROR_LIGHT,
    INFO_LIGHT,
    SUCCESS_LIGHT,
    WARNING_LIGHT,
)

# Colores de renglón alineados con style.py
_COLOR_ERROR = ERROR_LIGHT.name()
_COLOR_CANCEL = WARNING_LIGHT.name()
_COLOR_SUCCESS = SUCCESS_LIGHT.name()
_COLOR_INFO = INFO_LIGHT.name()


def _entry_color(message: str) -> str | None:
    """Devuelve el color HTML para la línea, o None para el color por defecto."""
    msg = message.lower()
    if msg.startswith("error"):
        return _COLOR_ERROR
    if msg.startswith("cancelaci"):
        return _COLOR_CANCEL
    if any(kw in msg for kw in ("completada", "exitosamente", "resultado", "cargados")):
        return _COLOR_SUCCESS
    if any(kw in msg for kw in ("proyecto", "abiert", "guardad", "erp")):
        return _COLOR_INFO
    return None


class LogPanel(QWidget):
    """Registro de eventos de ejecución, de solo lectura."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logPanel")

        self._text = QTextEdit(self)
        self._text.setObjectName("logText")
        self._text.setReadOnly(True)
        self._text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

        self._copy_button = QPushButton("Copiar", self)
        self._copy_button.setToolTip("Copiar el registro al portapapeles")
        self._copy_button.setFixedHeight(24)
        self._copy_button.setProperty("class", "compact")
        self._copy_button.clicked.connect(self._copy_to_clipboard)

        self._clear_button = QPushButton("Limpiar", self)
        self._clear_button.setToolTip("Limpiar el registro de esta sesión")
        self._clear_button.setFixedHeight(24)
        self._clear_button.setProperty("class", "compact")
        self._clear_button.clicked.connect(self.clear)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 2, 0, 0)
        btn_row.addStretch(1)
        btn_row.addWidget(self._copy_button)
        btn_row.addWidget(self._clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._text)
        layout.addLayout(btn_row)

    def append_entry(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = _entry_color(message)
        ts_html = f'<span style="color:#888888;">[{timestamp}]</span>'
        if color:
            msg_html = f'<span style="color:{color};">{escape(message)}</span>'
        else:
            msg_html = escape(message)
        self._text.append(f"{ts_html} {msg_html}")

    def clear(self) -> None:
        self._text.clear()

    def text(self) -> str:
        return self._text.toPlainText()

    def _copy_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._text.toPlainText())
