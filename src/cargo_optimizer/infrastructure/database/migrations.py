"""Inicialización de esquema y punto de extensión para migraciones futuras.

Solo existe la versión de esquema `"1"` en esta fase. Cuando exista una
versión `"2"`, este módulo debe seguir aceptando bases en versión `"1"`
y aplicar una migración real (`_migrate_1_to_2(engine)`) antes de
declarar la base como compatible — nunca basta con ampliar
`_SUPPORTED_SCHEMA_VERSIONS` sin escribir la migración. Una versión
desconocida (más nueva que la que la aplicación soporta) nunca se
adivina: se rechaza con `DatabaseMigrationError` y la base no se toca.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cargo_optimizer.infrastructure.database.exceptions import DatabaseMigrationError
from cargo_optimizer.infrastructure.database.orm_models import Base, SchemaMetadataORM

CURRENT_SCHEMA_VERSION = "1"
_SUPPORTED_SCHEMA_VERSIONS = frozenset({"1"})
_SCHEMA_VERSION_KEY = "schema_version"


def initialize_database(engine: Engine) -> None:
    """Crea las tablas si faltan y deja la base en la versión de esquema actual."""
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        row = session.get(SchemaMetadataORM, _SCHEMA_VERSION_KEY)
        if row is None:
            session.add(SchemaMetadataORM(key=_SCHEMA_VERSION_KEY, value=CURRENT_SCHEMA_VERSION))
            session.commit()
        else:
            _ensure_supported_schema_version(row.value)


def migrate_database(engine: Engine) -> None:
    """Verifica (y migraría, si existiera una versión futura) el esquema de una base ya creada."""
    with Session(engine) as session:
        version = session.scalar(
            select(SchemaMetadataORM.value).where(SchemaMetadataORM.key == _SCHEMA_VERSION_KEY)
        )
    if version is None:
        raise DatabaseMigrationError(
            "La base de datos no declara una versión de esquema (`schema_metadata` vacía)."
        )
    _ensure_supported_schema_version(version)


def read_schema_version(engine: Engine) -> str | None:
    with Session(engine) as session:
        return session.scalar(
            select(SchemaMetadataORM.value).where(SchemaMetadataORM.key == _SCHEMA_VERSION_KEY)
        )


def _ensure_supported_schema_version(version: str) -> None:
    if version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise DatabaseMigrationError(
            f"Esta versión de CargoOptimizer3D no reconoce el esquema de base de datos "
            f"'{version}'. Actualiza la aplicación para usar esta base."
        )
