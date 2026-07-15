"""`DatabaseManager`: dueño único del motor SQLAlchemy y de sus sesiones.

Sesiones siempre cortas (`session_scope`, un `with` por operación):
nunca se comparte una `Session` entre hilos ni se mantiene una
transacción abierta mientras un diálogo espera al usuario. El worker
de `PackingEngine` (`OptimizationWorker`, un `QThread`) nunca abre una
sesión de este módulo — el historial de una ejecución se registra
desde el hilo principal, después de recibir el `PackingResult` (ver
`docs/Database.md`).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from cargo_optimizer.infrastructure.database.exceptions import (
    DatabaseInitializationError,
    DatabaseMigrationError,
)
from cargo_optimizer.infrastructure.database.migrations import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    read_schema_version,
)

_BUSY_TIMEOUT_MS = 5000


@dataclass(frozen=True, slots=True)
class DatabaseHealth:
    """Resultado de `DatabaseManager.health_check()`: nunca lanza, siempre informa."""

    ok: bool
    detail: str


class DatabaseManager:
    """Crea el motor SQLite, inicializa el esquema y entrega sesiones cortas."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        try:
            self._engine = create_engine(f"sqlite:///{db_path}", future=True)
            self._configure_sqlite_pragmas(self._engine)
        except Exception as exc:
            raise DatabaseInitializationError(
                f"No se pudo crear el motor de base de datos en '{db_path}': {exc}"
            ) from exc
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @staticmethod
    def _configure_sqlite_pragmas(engine: Engine) -> None:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            cursor.close()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def initialize(self) -> None:
        """Crea las tablas si faltan y deja la base en la versión de esquema actual.

        Deja pasar `DatabaseMigrationError` tal cual (versión de esquema
        no reconocida: nunca se adivina ni se modifica la base); envuelve
        cualquier otro fallo en `DatabaseInitializationError`.
        """
        try:
            initialize_database(self._engine)
        except DatabaseMigrationError:
            raise
        except Exception as exc:
            raise DatabaseInitializationError(
                f"No se pudo inicializar el esquema de la base de datos: {exc}"
            ) from exc

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Una sesión por operación: commit si todo va bien, rollback y propagación si no."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def schema_version(self) -> str | None:
        return read_schema_version(self._engine)

    def health_check(self) -> DatabaseHealth:
        try:
            with self.session_scope() as session:
                session.execute(select(1))
            version = self.schema_version()
        except Exception as exc:
            return DatabaseHealth(ok=False, detail=str(exc))
        if version != CURRENT_SCHEMA_VERSION:
            return DatabaseHealth(ok=False, detail=f"Versión de esquema inesperada: {version!r}")
        return DatabaseHealth(ok=True, detail="La base de datos responde correctamente.")

    def backup(self, destination: Path | None = None) -> Path:
        """Copia de seguridad mediante la API de backup de `sqlite3` (segura con la base en uso)."""
        target = destination or self._db_path.with_name(
            f"{self._db_path.stem}_backup_"
            f"{datetime.now(UTC):%Y%m%d%H%M%S}{self._db_path.suffix}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        source_connection = sqlite3.connect(str(self._db_path))
        try:
            destination_connection = sqlite3.connect(str(target))
            try:
                source_connection.backup(destination_connection)
            finally:
                destination_connection.close()
        finally:
            source_connection.close()
        return target

    def close(self) -> None:
        self._engine.dispose()
