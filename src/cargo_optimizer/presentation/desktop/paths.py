"""Resolución de rutas de recursos empaquetados con la aplicación (iconos, etc.).

Distinto de `infrastructure/database/paths.py::get_user_database_path`
(esa resuelve dónde **escribir** datos del usuario, en
`%LOCALAPPDATA%`); esta resuelve dónde **leer** recursos de solo
lectura empaquetados junto al propio código.

`Path(__file__).parent` funciona al ejecutar desde el código fuente,
pero no es fiable dentro de un build de PyInstaller: los módulos `.py`
se empaquetan comprimidos en un archivo PYZ, no como archivos sueltos
en disco, así que `__file__` de un módulo congelado no necesariamente
vive junto a los recursos reales que sí se copiaron tal cual (ver
`packaging/CargoOptimizer3D.spec`, sección `datas`). PyInstaller
expone `sys.frozen`/`sys._MEIPASS` para resolver esto de forma
oficial: en modo `onedir` (el que usa este proyecto — ver
`docs/ADR/ADR-0013-empaquetado-windows.md`), `sys._MEIPASS` apunta al
propio directorio de la distribución (no a un directorio temporal
como en `onefile`).
"""

from __future__ import annotations

import sys
from pathlib import Path


def presentation_desktop_root() -> Path:
    """Directorio base para resolver recursos de `presentation/desktop`.

    Funciona igual ejecutando desde el código fuente
    (`python -m cargo_optimizer`) que desde el build empaquetado con
    PyInstaller — es la única diferencia entre ambos entornos que
    `icons.py` necesita conocer.
    """
    frozen_base = getattr(sys, "_MEIPASS", None)
    if frozen_base is not None:
        return Path(frozen_base) / "cargo_optimizer" / "presentation" / "desktop"
    return Path(__file__).parent
