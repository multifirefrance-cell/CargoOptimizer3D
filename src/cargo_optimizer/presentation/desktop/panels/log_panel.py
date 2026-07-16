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

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    """Registro de eventos de ejecución, de solo lectura."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logPanel")

        self._text = QPlainTextEdit(self)
        self._text.setObjectName("logText")
        self._text.setReadOnly(True)
        self._text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

    def append_entry(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.appendPlainText(f"[{timestamp}] {message}")

    def clear(self) -> None:
        self._text.clear()

    def text(self) -> str:
        return self._text.toPlainText()
