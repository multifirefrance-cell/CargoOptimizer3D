"""Punto de arranque de la aplicación de escritorio."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer import __version__
from cargo_optimizer.presentation.desktop.main_window import MainWindow


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setApplicationName("CargoOptimizer3D")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()

    return app.exec()
