"""Pruebas de `MainWindow`: creación, estructura y persistencia de QSettings."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QToolBar

from cargo_optimizer import __version__
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import _KEY_MAIN_WINDOW_GEOMETRY, AppSettings


def _allow_close_without_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    """Responde "Descartar" al preguntar por cambios sin guardar (fase 7.0), ver `closeEvent`."""

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))


_EXPECTED_MENUS = (
    "&Archivo",
    "&Proyecto",
    "&Espacio de carga",
    "Pro&ductos",
    "&Optimización",
    "&Ver",
    "&Herramientas",
    "A&yuda",
)


def test_main_window_creates_without_error(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    assert window.windowTitle().startswith(f"CargoOptimizer3D v{__version__}")
    assert "Proyecto sin guardar" in window.windowTitle()
    window.close()


def test_main_window_has_all_required_menus(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    menu_titles = [action.text() for action in window.menuBar().actions()]
    for expected in _EXPECTED_MENUS:
        assert expected in menu_titles
    window.close()


def test_toolbar_has_required_actions(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    toolbar = window.findChild(QToolBar, "mainToolBar")
    assert toolbar is not None
    action_texts = {
        action.text().replace("&", "").replace("…", "")
        for action in toolbar.actions()
        if action.text()
    }
    for expected in (
        "Nuevo",
        "Abrir",
        "Guardar",
        "Importar Excel",
        "Ejecutar optimización",
        "Cancelar",
    ):
        assert expected in action_texts
    window.close()


def test_status_bar_shows_project_engine_and_state(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.statusBar() is not None
    assert window._project_status_label.text() != ""
    assert "Motor" in window._engine_status_label.text()
    assert "Estado" in window._state_status_label.text()
    window.close()


def test_unimplemented_action_shows_status_message(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window.action_check_updates.trigger()
    assert "próxima versión" in window.statusBar().currentMessage()
    window.close()


def test_new_product_action_adds_row_to_table(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    initial_rows = window.product_table_panel.model.rowCount()
    window.action_new_product.trigger()
    assert window.product_table_panel.model.rowCount() == initial_rows + 1
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_close_event_persists_window_state(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    window.resize(1000, 700)
    expected_bytes = window.saveGeometry()
    window.close()

    stored_bytes = app_settings.qsettings.value(_KEY_MAIN_WINDOW_GEOMETRY)
    assert stored_bytes == expected_bytes

    restored = MainWindow(app_settings)  # no debe lanzar excepción al restaurar
    restored.close()


def test_toggle_theme_updates_settings(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    window.action_dark_theme.trigger()
    assert app_settings.theme() == "dark"
    window.action_light_theme.trigger()
    assert app_settings.theme() == "light"
    window.close()


def test_selection_details_dock_hidden_by_default(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Rediseño "workspace operativo": el panel "Guía" desaparece por completo
    # y el dock de detalles de selección solo se muestra cuando el usuario
    # selecciona una caja en el visor 3D (nunca por defecto al arrancar).
    window = MainWindow(app_settings)
    window.show()
    assert not window.selection_details_dock.isVisible()
    window.close()
