"""Carga de iconos SVG propios de `presentation/desktop`.

Los recursos viven junto al adaptador que los usa
(`presentation/desktop/resources/icons/`), no en un directorio
compartido a nivel de proyecto — ver `docs/Architecture.md`. Se cargan
por ruta de archivo directamente (`QIcon(str(path))`); no hay todavía
un pipeline `.qrc`/`pyside6-rcc` porque no aporta nada con el número
actual de iconos y añadiría un paso de build que no existe hoy.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

_ICONS_DIR = Path(__file__).parent / "resources" / "icons"


def icon(name: str) -> QIcon:
    """Carga `resources/icons/{name}.svg`. Devuelve un `QIcon` nulo si no existe."""
    path = _ICONS_DIR / f"{name}.svg"
    return QIcon(str(path)) if path.is_file() else QIcon()
