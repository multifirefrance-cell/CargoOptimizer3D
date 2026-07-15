"""Persistencia de preferencias de interfaz mediante `QSettings`.

Fase 5.0: solo `QSettings` (registro de Windows / archivo INI nativo
según plataforma). No se crea SQLite ni ningún otro almacenamiento aquí
— eso pertenece a fases posteriores (persistencia de proyectos, fase
7). Lo que se guarda es exclusivamente estado de la propia interfaz
(tamaños, posiciones, último directorio, último perfil), nunca datos de
negocio (`LoadingSpace`, `LoadUnit`).

`AppSettings` acepta una `QSettings` inyectada para que los tests
puedan usar un archivo temporal en vez de tocar el registro real del
usuario que ejecuta la suite.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QHeaderView, QMainWindow, QSplitter

ORGANIZATION_NAME = "CargoOptimizer3D"
APPLICATION_NAME = "CargoOptimizer3D"

_KEY_MAIN_WINDOW_GEOMETRY = "mainWindow/geometry"
_KEY_MAIN_WINDOW_STATE = "mainWindow/state"
_KEY_LAST_DIRECTORY = "session/lastDirectory"
_KEY_LAST_LOADING_SPACE_PROFILE = "session/lastLoadingSpaceProfile"
_KEY_THEME = "appearance/theme"
_KEY_RECENT_PROJECT_FILES = "session/recentProjectFiles"

MAX_RECENT_PROJECT_FILES = 10


def _splitter_key(name: str) -> str:
    return f"splitters/{name}"


def _header_key(name: str) -> str:
    return f"headers/{name}"


class AppSettings:
    """Wrapper delgado sobre `QSettings`: nombres de clave centralizados, nunca dispersos."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

    @property
    def qsettings(self) -> QSettings:
        return self._settings

    def save_main_window_state(self, window: QMainWindow) -> None:
        self._settings.setValue(_KEY_MAIN_WINDOW_GEOMETRY, window.saveGeometry())
        self._settings.setValue(_KEY_MAIN_WINDOW_STATE, window.saveState())

    def restore_main_window_state(self, window: QMainWindow) -> None:
        geometry = self._settings.value(_KEY_MAIN_WINDOW_GEOMETRY)
        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            window.restoreGeometry(geometry)
        state = self._settings.value(_KEY_MAIN_WINDOW_STATE)
        if isinstance(state, QByteArray) and not state.isEmpty():
            window.restoreState(state)

    def save_splitter_state(self, name: str, splitter: QSplitter) -> None:
        self._settings.setValue(_splitter_key(name), splitter.saveState())

    def restore_splitter_state(self, name: str, splitter: QSplitter) -> None:
        state = self._settings.value(_splitter_key(name))
        if isinstance(state, QByteArray) and not state.isEmpty():
            splitter.restoreState(state)

    def save_header_state(self, name: str, header: QHeaderView) -> None:
        self._settings.setValue(_header_key(name), header.saveState())

    def restore_header_state(self, name: str, header: QHeaderView) -> None:
        state = self._settings.value(_header_key(name))
        if isinstance(state, QByteArray) and not state.isEmpty():
            header.restoreState(state)

    def last_directory(self) -> str:
        value = self._settings.value(_KEY_LAST_DIRECTORY, "")
        return str(value) if value is not None else ""

    def set_last_directory(self, path: str) -> None:
        self._settings.setValue(_KEY_LAST_DIRECTORY, path)

    def last_loading_space_profile(self) -> str:
        value = self._settings.value(_KEY_LAST_LOADING_SPACE_PROFILE, "")
        return str(value) if value is not None else ""

    def set_last_loading_space_profile(self, profile_key: str) -> None:
        self._settings.setValue(_KEY_LAST_LOADING_SPACE_PROFILE, profile_key)

    def theme(self) -> str:
        value = self._settings.value(_KEY_THEME, "light")
        return str(value) if value is not None else "light"

    def set_theme(self, theme: str) -> None:
        self._settings.setValue(_KEY_THEME, theme)

    def recent_project_files(self) -> list[str]:
        """Últimos proyectos abiertos/guardados, más reciente primero.

        `QSettings` puede devolver un único string en vez de una lista
        de un elemento (comportamiento de fábrica en algunos backends),
        de ahí la normalización explícita.
        """
        value = self._settings.value(_KEY_RECENT_PROJECT_FILES, [])
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    def set_recent_project_files(self, paths: list[str]) -> None:
        self._settings.setValue(_KEY_RECENT_PROJECT_FILES, paths[:MAX_RECENT_PROJECT_FILES])

    def add_recent_project_file(self, path: str) -> None:
        """Inserta `path` al frente de la lista (sin duplicados), recortando a las últimas 10."""
        existing = [p for p in self.recent_project_files() if p != path]
        existing.insert(0, path)
        self.set_recent_project_files(existing)

    def sync(self) -> None:
        self._settings.sync()
