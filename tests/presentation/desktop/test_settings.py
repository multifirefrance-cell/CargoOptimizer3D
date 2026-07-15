"""Pruebas de `AppSettings`: persistencia de interfaz vía `QSettings`.

Cada prueba usa `app_settings` (fixture con un archivo INI temporal),
nunca el registro real del usuario que ejecuta la suite.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QSplitter

from cargo_optimizer.presentation.desktop.settings import (
    _KEY_MAIN_WINDOW_GEOMETRY,
    AppSettings,
    _splitter_key,
)


def test_last_directory_round_trips(app_settings: AppSettings) -> None:
    assert app_settings.last_directory() == ""
    app_settings.set_last_directory("C:/Users/example/Documents")
    assert app_settings.last_directory() == "C:/Users/example/Documents"


def test_last_loading_space_profile_round_trips(app_settings: AppSettings) -> None:
    assert app_settings.last_loading_space_profile() == ""
    app_settings.set_last_loading_space_profile("Contenedor 40'")
    assert app_settings.last_loading_space_profile() == "Contenedor 40'"


def test_theme_defaults_to_light(app_settings: AppSettings) -> None:
    assert app_settings.theme() == "light"


def test_theme_round_trips(app_settings: AppSettings) -> None:
    app_settings.set_theme("dark")
    assert app_settings.theme() == "dark"


def test_main_window_geometry_round_trips(app_settings: AppSettings) -> None:
    # Compara los bytes persistidos, no el tamaño real de la ventana tras
    # restoreGeometry(): la plataforma Qt "offscreen" usada en tests no
    # garantiza un tamaño de pantalla virtual igual al de un entorno con
    # display real, así que Qt puede ajustar la geometría restaurada. Lo que
    # sí debe ser exacto es que AppSettings guarda y devuelve los mismos
    # bytes que produce/consume la propia API de Qt (`saveGeometry`).
    window = QMainWindow()
    window.resize(950, 640)
    expected_bytes = window.saveGeometry()
    app_settings.save_main_window_state(window)

    stored_bytes = app_settings.qsettings.value(_KEY_MAIN_WINDOW_GEOMETRY)
    assert stored_bytes == expected_bytes

    restored = QMainWindow()
    app_settings.restore_main_window_state(restored)  # no debe lanzar excepción


def test_splitter_state_round_trips(app_settings: AppSettings) -> None:
    original = QSplitter()
    original.addWidget(QSplitter())
    original.addWidget(QSplitter())
    original.resize(400, 200)
    original.setSizes([300, 100])
    expected_bytes = original.saveState()
    app_settings.save_splitter_state("test", original)

    stored_bytes = app_settings.qsettings.value(_splitter_key("test"))
    assert stored_bytes == expected_bytes

    restored = QSplitter()
    restored.addWidget(QSplitter())
    restored.addWidget(QSplitter())
    restored.resize(400, 200)
    app_settings.restore_splitter_state("test", restored)  # no debe lanzar excepción


def test_restoring_without_prior_save_does_not_raise(app_settings: AppSettings) -> None:
    window = QMainWindow()
    app_settings.restore_main_window_state(window)  # no debe lanzar excepción
    splitter = QSplitter()
    app_settings.restore_splitter_state("never-saved", splitter)  # no debe lanzar excepción
