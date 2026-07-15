"""Fixtures compartidas para las pruebas de `infrastructure/database`.

Toda prueba usa una base SQLite temporal por prueba (`tmp_path`):
nunca la base real del usuario.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path


@pytest.fixture
def db_manager(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return manager
