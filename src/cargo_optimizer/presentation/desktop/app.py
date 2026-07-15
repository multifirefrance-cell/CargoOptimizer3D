"""Punto de arranque de la aplicación de escritorio."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer import __version__
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import (
    APPLICATION_NAME,
    ORGANIZATION_NAME,
    AppSettings,
)
from cargo_optimizer.presentation.desktop.style import apply_theme


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationVersion(__version__)

    settings = AppSettings()
    apply_theme(app, settings.theme())

    window = MainWindow(settings)
    window.show()

    return app.exec()
