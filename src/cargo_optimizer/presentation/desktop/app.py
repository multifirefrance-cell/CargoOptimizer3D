"""Punto de arranque de la aplicación de escritorio."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer import __version__
from cargo_optimizer.infrastructure.database import CatalogService, DatabaseError
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

    catalog_service, catalog_error = _initialize_catalog_service()

    window = MainWindow(settings, catalog_service=catalog_service, catalog_error=catalog_error)
    window.show()

    return app.exec()


def _initialize_catalog_service() -> tuple[CatalogService | None, str | None]:
    """Nunca deja que un fallo de SQLite impida abrir la aplicación (modo limitado, fase 7.1)."""
    try:
        return CatalogService.create_default(), None
    except DatabaseError as exc:
        return None, str(exc)
