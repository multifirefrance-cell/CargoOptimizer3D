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
from PySide6.QtWidgets import QApplication, QMessageBox

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


@pytest.fixture(autouse=True)
def _no_blocking_question_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Red de seguridad: `QMessageBox.question` nunca debe abrir un diálogo real en esta suite.

    Desde la fase 7.0, `MainWindow.closeEvent`/`_on_new_project`/etc.
    llaman a `QMessageBox.question` cuando hay cambios sin guardar (ver
    `_confirm_discard_unsaved_changes`). Bajo la plataforma `offscreen`
    un diálogo real se queda esperando un clic que nunca llega y cuelga
    el proceso de pytest. El valor por defecto aquí es "Descartar" (la
    opción menos sorprendente para una prueba que no pidió guardar
    explícitamente); cualquier prueba que necesite otra respuesta
    (Guardar/Cancelar) sobrescribe este parche con su propio
    `monkeypatch.setattr(QMessageBox, "question", ...)`, que gana por
    aplicarse después.
    """

    def _fake(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))
