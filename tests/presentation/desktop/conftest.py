"""Fixtures compartidas para las pruebas de `presentation/desktop`.

Fuerza la plataforma Qt `offscreen` antes de importar cualquier cosa de
PySide6, para que la suite nunca abra ventanas reales ni dependa de que
haya un entorno gráfico disponible (CI incluido). Solo puede existir un
`QApplication` por proceso, así que se crea una única vez por sesión de
pytest y se reutiliza en todas las pruebas.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.settings import AppSettings


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    app = QApplication.instance()
    created = app is None
    if app is None:
        app = QApplication([])
    yield app
    if created:
        app.quit()


@pytest.fixture
def app_settings(tmp_path: Path, qapp: QApplication) -> AppSettings:
    """`AppSettings` respaldado por un archivo INI temporal, nunca el registro real."""
    ini_path = str(tmp_path / "test_settings.ini")
    qsettings = QSettings(ini_path, QSettings.Format.IniFormat)
    return AppSettings(qsettings)
