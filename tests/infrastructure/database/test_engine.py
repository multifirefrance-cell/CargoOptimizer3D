"""Pruebas de `DatabaseManager`: inicialización, esquema, sesiones, backup, modo limitado."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import DatabaseMigrationError
from cargo_optimizer.infrastructure.database.migrations import CURRENT_SCHEMA_VERSION
from cargo_optimizer.infrastructure.database.orm_models import SchemaMetadataORM
from cargo_optimizer.infrastructure.database.paths import get_user_database_path


def _fresh_manager(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    return manager


def test_initialize_creates_schema_version(tmp_path: Path) -> None:
    manager = _fresh_manager(tmp_path)
    assert manager.schema_version() == CURRENT_SCHEMA_VERSION
    manager.close()


def test_initialize_is_idempotent(tmp_path: Path) -> None:
    manager = _fresh_manager(tmp_path)
    manager.initialize()
    assert manager.schema_version() == CURRENT_SCHEMA_VERSION
    manager.close()


def test_health_check_ok_after_initialize(db_manager: DatabaseManager) -> None:
    health = db_manager.health_check()
    assert health.ok is True


def test_future_schema_version_raises_migration_error(db_manager: DatabaseManager) -> None:
    with db_manager.session_scope() as session:
        row = session.get(SchemaMetadataORM, "schema_version")
        assert row is not None
        row.value = "99"

    with pytest.raises(DatabaseMigrationError):
        db_manager.initialize()


def test_health_check_reports_future_schema_version(db_manager: DatabaseManager) -> None:
    with db_manager.session_scope() as session:
        row = session.get(SchemaMetadataORM, "schema_version")
        assert row is not None
        row.value = "99"

    health = db_manager.health_check()
    assert health.ok is False


def test_session_scope_commits_on_success(db_manager: DatabaseManager) -> None:
    with db_manager.session_scope() as session:
        session.add(SchemaMetadataORM(key="custom", value="1"))

    with db_manager.session_scope() as session:
        assert session.get(SchemaMetadataORM, "custom") is not None


def test_session_scope_rolls_back_on_exception(db_manager: DatabaseManager) -> None:
    with pytest.raises(ValueError, match="boom"), db_manager.session_scope() as session:
        session.add(SchemaMetadataORM(key="rolled_back", value="x"))
        raise ValueError("boom")

    with db_manager.session_scope() as session:
        assert session.get(SchemaMetadataORM, "rolled_back") is None


def test_foreign_keys_pragma_is_enabled(db_manager: DatabaseManager) -> None:
    with db_manager.session_scope() as session:
        value = session.connection().exec_driver_sql("PRAGMA foreign_keys").scalar()
        assert value == 1


def test_select_one_works_through_session_scope(db_manager: DatabaseManager) -> None:
    with db_manager.session_scope() as session:
        assert session.execute(select(1)).scalar() == 1


def test_backup_creates_a_working_copy(db_manager: DatabaseManager) -> None:
    backup_path = db_manager.backup()
    assert backup_path.exists()
    backup_manager = DatabaseManager(backup_path)
    assert backup_manager.schema_version() == CURRENT_SCHEMA_VERSION
    backup_manager.close()


def test_backup_to_explicit_destination(db_manager: DatabaseManager, tmp_path: Path) -> None:
    destination = tmp_path / "explicit_backup.db"
    result = db_manager.backup(destination)
    assert result == destination
    assert destination.exists()


def test_corrupt_database_file_reported_by_health_check(tmp_path: Path) -> None:
    db_path = get_user_database_path(base_dir=tmp_path)
    db_path.write_text("esto no es una base de datos SQLite valida", encoding="utf-8")
    manager = DatabaseManager(db_path)
    health = manager.health_check()
    assert health.ok is False
    manager.close()
