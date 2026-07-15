"""`CatalogService`: fachada única que `presentation` usa para el catálogo/perfiles/historial.

Agrupa los cinco repositorios (catálogo, perfiles de espacio, perfiles
de mapeo de columnas de Excel, historial de proyectos, historial de
ejecuciones) y añade únicamente la lógica que no encaja en ninguno de
ellos por sí sola: copiar un `LoadUnit`/`LoadingSpace` del catálogo a
un proyecto concreto, generando una identidad nueva para que el
proyecto quede completamente independiente del catálogo (ver
`docs/Database.md`, sección "Diferencias con `.cargo3d`" — un cambio
futuro en el catálogo nunca debe alterar un proyecto ya guardado). No
es un *God Object*: no reimplementa nada de los repositorios, solo los
expone juntos y añade estas dos operaciones.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.engine import DatabaseHealth, DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import (
    ImportMappingProfileRepository,
    LoadingSpaceProfileRepository,
    PackingRunHistoryRepository,
    ProductCatalogRepository,
    ProjectHistoryRepository,
)


class CatalogService:
    """Punto de entrada único de `infrastructure/database` para `presentation`."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.database = db_manager
        self.products = ProductCatalogRepository(db_manager)
        self.profiles = LoadingSpaceProfileRepository(db_manager)
        self.import_mappings = ImportMappingProfileRepository(db_manager)
        self.project_history = ProjectHistoryRepository(db_manager)
        self.run_history = PackingRunHistoryRepository(db_manager)

    @classmethod
    def create_default(cls, *, base_dir: Path | None = None) -> CatalogService:
        """Inicializa la base (ubicación estándar o `base_dir` en tests) y los perfiles builtin.

        Puede lanzar `DatabaseError` (o cualquiera de sus subclases):
        quien la llame decide si la aplicación continúa en modo
        limitado (ver `app.py`), nunca se asume aquí.
        """
        db_manager = DatabaseManager(get_user_database_path(base_dir=base_dir))
        db_manager.initialize()
        service = cls(db_manager)
        service.profiles.ensure_builtin_profiles()
        service.import_mappings.ensure_builtin_profiles()
        return service

    def health_check(self) -> DatabaseHealth:
        return self.database.health_check()

    @staticmethod
    def copy_to_project(load_unit: LoadUnit) -> LoadUnit:
        """Copia independiente de un `LoadUnit` de catálogo, con un UUID nuevo para el proyecto."""
        return replace(load_unit, id=uuid4())

    @staticmethod
    def copy_profile_to_project(space: LoadingSpace) -> LoadingSpace:
        """Copia independiente de un perfil de espacio, con un UUID nuevo para el proyecto."""
        return replace(space, id=uuid4())

    def close(self) -> None:
        self.database.close()
