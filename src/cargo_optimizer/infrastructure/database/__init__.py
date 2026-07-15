"""Catálogo de productos, perfiles de espacio e historial en SQLite (fase 7.1).

Ver `docs/Database.md` para el esquema completo y la diferencia con la
persistencia de proyectos `.cargo3d` (`infrastructure/persistence/`,
fase 7.0). API pública: `CatalogService` (`catalog_service.py`).
"""

from __future__ import annotations

from cargo_optimizer.infrastructure.database.catalog_service import CatalogService
from cargo_optimizer.infrastructure.database.engine import DatabaseHealth, DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import (
    DatabaseError,
    DatabaseInitializationError,
    DatabaseMigrationError,
    DuplicateCatalogSkuError,
    DuplicateImportMappingProfileError,
    DuplicateLoadingSpaceProfileError,
    RecordNotFoundError,
    RepositoryError,
)
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import (
    CatalogProductEntry,
    ImportMappingProfileEntry,
    ImportMappingProfileRepository,
    LoadingSpaceProfileEntry,
    LoadingSpaceProfileRepository,
    PackingRunHistoryEntry,
    PackingRunHistoryRepository,
    ProductCatalogRepository,
    ProjectHistoryEntry,
    ProjectHistoryRepository,
)

__all__ = [
    "CatalogProductEntry",
    "CatalogService",
    "DatabaseError",
    "DatabaseHealth",
    "DatabaseInitializationError",
    "DatabaseManager",
    "DatabaseMigrationError",
    "DuplicateCatalogSkuError",
    "DuplicateImportMappingProfileError",
    "DuplicateLoadingSpaceProfileError",
    "ImportMappingProfileEntry",
    "ImportMappingProfileRepository",
    "LoadingSpaceProfileEntry",
    "LoadingSpaceProfileRepository",
    "PackingRunHistoryEntry",
    "PackingRunHistoryRepository",
    "ProductCatalogRepository",
    "ProjectHistoryEntry",
    "ProjectHistoryRepository",
    "RecordNotFoundError",
    "RepositoryError",
    "get_user_database_path",
]
