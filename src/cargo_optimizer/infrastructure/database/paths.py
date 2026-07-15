"""Ubicación del archivo SQLite del catálogo/historial.

No depende de Qt: `%LOCALAPPDATA%` se lee directamente del entorno, no
de `QStandardPaths`, para que este módulo sea importable y testeable
sin ninguna dependencia de PySide6 (misma disciplina que el resto de
`infrastructure`).
"""

from __future__ import annotations

import os
from pathlib import Path

_APPLICATION_DIR_NAME = "CargoOptimizer3D"
_DATABASE_FILE_NAME = "cargo_optimizer.db"


def get_user_database_path(*, base_dir: Path | None = None) -> Path:
    """Ruta del archivo SQLite del usuario actual, creando el directorio si falta.

    `base_dir` permite a los tests apuntar a un directorio temporal en
    vez de `%LOCALAPPDATA%` — nunca se usa la base real del usuario en
    la suite de pruebas.
    """
    if base_dir is not None:
        directory = base_dir
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        root = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
        directory = root / _APPLICATION_DIR_NAME

    directory.mkdir(parents=True, exist_ok=True)
    return directory / _DATABASE_FILE_NAME
