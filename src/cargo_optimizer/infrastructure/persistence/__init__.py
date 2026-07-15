"""Persistencia de proyectos en archivos ``.cargo3d`` (JSON versionado, fase 7.0).

Ver `docs/ProjectFiles.md` para el formato completo. API pública:
``ProjectFileRepository`` (`project_file_repository.py`).
"""

from __future__ import annotations

from cargo_optimizer.infrastructure.persistence.exceptions import (
    ProjectFileCorruptError,
    ProjectFileError,
    ProjectFileNotFoundError,
    ProjectFileWriteError,
    UnsupportedSchemaVersionError,
)
from cargo_optimizer.infrastructure.persistence.project_file_repository import (
    CURRENT_SCHEMA_VERSION,
    FORMAT_NAME,
    LoadedProjectFile,
    ProjectFileMetadata,
    ProjectFileRepository,
)

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "FORMAT_NAME",
    "LoadedProjectFile",
    "ProjectFileCorruptError",
    "ProjectFileError",
    "ProjectFileMetadata",
    "ProjectFileNotFoundError",
    "ProjectFileRepository",
    "ProjectFileWriteError",
    "UnsupportedSchemaVersionError",
]
