"""`ProjectFileRepository`: lectura y escritura de archivos de proyecto `.cargo3d`.

Ver `docs/ProjectFiles.md` para el formato completo del archivo. Reglas
de esta implementación (fase 7.0):

- JSON UTF-8 legible por un humano (``json.dumps(..., indent=2)``),
  nunca ``pickle``, ``jsonpickle`` ni volcado de ``__dict__`` — cada
  tipo de dominio se traduce explícitamente en `serialization.py`.
- Escritura atómica: se escribe primero un archivo temporal en el mismo
  directorio y se reemplaza con ``os.replace`` (atómico en Windows y
  POSIX), para que una escritura interrumpida nunca dañe el archivo
  anterior.
- Copia de seguridad automática: antes de sobrescribir un archivo
  existente, se copia su contenido actual a ``<archivo>.cargo3d.bak``.
- ``schema_version`` es un campo del propio archivo, distinto de
  ``application_version``: un archivo puede sobrevivir a varias
  versiones de la aplicación mientras el esquema no cambie. Hoy solo
  existe la versión "1.0"; ``_ensure_supported_schema_version`` es el
  único punto que hay que tocar para añadir una migración futura (ver
  también su docstring).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from shutil import copyfile
from typing import Any

from cargo_optimizer.domain.exceptions import DomainValidationError, DuplicateSkuError
from cargo_optimizer.domain.project import CargoProject
from cargo_optimizer.infrastructure.persistence.exceptions import (
    ProjectFileCorruptError,
    ProjectFileError,
    ProjectFileNotFoundError,
    ProjectFileWriteError,
    UnsupportedSchemaVersionError,
)
from cargo_optimizer.infrastructure.persistence.serialization import (
    JSONDict,
    cargo_project_from_dict,
    cargo_project_to_dict,
)

FORMAT_NAME = "cargo_optimizer3d_project"
CURRENT_SCHEMA_VERSION = "1.0"

# Versiones de esquema que esta versión de la aplicación sabe leer.
# Añadir una migración futura: incluir la versión antigua aquí y
# encadenar una función `_migrate_<vieja>_to_<nueva>(data) -> JSONDict`
# dentro de `_ensure_supported_schema_version`/`_migrate`, nunca
# reescribir `CURRENT_SCHEMA_VERSION` retroactivamente.
_SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})

_BACKUP_SUFFIX = ".bak"


@dataclass(frozen=True, slots=True)
class ProjectFileMetadata:
    """Metadatos del archivo `.cargo3d`, independientes del contenido del proyecto."""

    format_name: str
    schema_version: str
    application_version: str
    created_at: datetime
    modified_at: datetime


@dataclass(frozen=True, slots=True)
class LoadedProjectFile:
    """Resultado de `ProjectFileRepository.load`: proyecto reconstruido + metadatos + estado de UI.

    ``presentation_state`` es un diccionario opaco para esta capa: lo
    escribe y lo interpreta exclusivamente `presentation/desktop`
    (tema, splitters, docks visibles, si el último resultado quedó
    invalidado). `infrastructure` nunca necesita saber qué claves
    contiene — ver ADR de la fase 7.0 en `docs/ProjectFiles.md`.
    """

    project: CargoProject
    metadata: ProjectFileMetadata
    presentation_state: dict[str, Any] = field(default_factory=dict)


def _ensure_supported_schema_version(schema_version: str) -> None:
    """Único punto de extensión para migraciones futuras de esquema.

    Hoy solo existe "1.0": cualquier otro valor se rechaza. Cuando
    exista una versión "1.1", esta función debe seguir aceptando "1.0"
    (para archivos antiguos) y aplicar la migración correspondiente
    antes de reconstruir el proyecto — no basta con ampliar este
    conjunto sin escribir la migración real.
    """
    if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSchemaVersionError(
            f"Esta versión de CargoOptimizer3D no reconoce el esquema de proyecto "
            f"'{schema_version}'. Actualiza la aplicación para abrir este archivo."
        )


class ProjectFileRepository:
    """Guarda y carga proyectos completos como archivos `.cargo3d` (JSON versionado)."""

    def save(
        self,
        project: CargoProject,
        path: Path,
        *,
        application_version: str,
        presentation_state: Mapping[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> ProjectFileMetadata:
        """Escribe `project` en `path`, con backup automático y escritura atómica.

        `created_at` permite conservar la fecha de creación original a
        través de guardados sucesivos; si es `None` y `path` ya existe,
        se intenta leer del archivo anterior (de forma tolerante: un
        archivo anterior corrupto no debe impedir guardarlo de nuevo).
        """
        path = Path(path)
        resolved_created_at = created_at
        if resolved_created_at is None and path.exists():
            resolved_created_at = self._best_effort_created_at(path)
        if resolved_created_at is None:
            resolved_created_at = datetime.now(UTC)
        modified_at = datetime.now(UTC)

        envelope: JSONDict = {
            "format_name": FORMAT_NAME,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "application_version": application_version,
            "created_at": resolved_created_at.isoformat(),
            "modified_at": modified_at.isoformat(),
            "project": cargo_project_to_dict(project),
            "presentation_state": dict(presentation_state) if presentation_state else {},
        }
        text = json.dumps(envelope, indent=2, ensure_ascii=False)

        if path.exists():
            self.backup(path)

        try:
            self._write_atomic(path, text)
        except OSError as exc:
            raise ProjectFileWriteError(f"No se pudo escribir '{path}': {exc}") from exc

        return ProjectFileMetadata(
            format_name=FORMAT_NAME,
            schema_version=CURRENT_SCHEMA_VERSION,
            application_version=application_version,
            created_at=resolved_created_at,
            modified_at=modified_at,
        )

    def load(self, path: Path) -> LoadedProjectFile:
        """Lee y reconstruye un proyecto completo desde `path`.

        Lanza `ProjectFileNotFoundError`, `ProjectFileCorruptError` o
        `UnsupportedSchemaVersionError` — nunca una excepción de
        `json`/`domain` sin traducir.
        """
        data = self._read_json(path)
        metadata = self._parse_metadata(data, path)
        try:
            project = cargo_project_from_dict(data["project"])
        except (KeyError, TypeError, ValueError, DomainValidationError, DuplicateSkuError) as exc:
            raise ProjectFileCorruptError(
                f"El proyecto contenido en '{path}' está corrupto o no es válido: {exc}"
            ) from exc

        presentation_state = data.get("presentation_state")
        if not isinstance(presentation_state, dict):
            presentation_state = {}

        return LoadedProjectFile(
            project=project, metadata=metadata, presentation_state=presentation_state
        )

    def validate(self, path: Path) -> ProjectFileMetadata:
        """Comprueba que `path` es un archivo de proyecto válido, sin reconstruirlo por completo.

        Más barato que `load` cuando solo hace falta saber si el
        archivo se puede abrir (p. ej. al depurar la lista de
        proyectos recientes).
        """
        data = self._read_json(path)
        return self._parse_metadata(data, path)

    def backup(self, path: Path) -> Path | None:
        """Copia `path` a `<path>.bak` si existe. Devuelve la ruta del backup, o `None`."""
        path = Path(path)
        if not path.is_file():
            return None
        backup_path = path.with_name(path.name + _BACKUP_SUFFIX)
        try:
            copyfile(path, backup_path)
        except OSError as exc:
            raise ProjectFileWriteError(
                f"No se pudo crear la copia de seguridad de '{path}': {exc}"
            ) from exc
        return backup_path

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _best_effort_created_at(self, path: Path) -> datetime | None:
        try:
            data = self._read_json(path)
            return datetime.fromisoformat(str(data["created_at"]))
        except (ProjectFileError, KeyError, ValueError):
            return None

    def _read_json(self, path: Path) -> JSONDict:
        path = Path(path)
        if not path.is_file():
            raise ProjectFileNotFoundError(f"No existe el archivo de proyecto: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProjectFileError(f"No se pudo leer '{path}': {exc}") from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectFileCorruptError(f"'{path}' no contiene JSON válido: {exc}") from exc
        if not isinstance(data, dict):
            raise ProjectFileCorruptError(
                f"'{path}' no tiene la estructura esperada de un proyecto CargoOptimizer3D."
            )
        return data

    def _parse_metadata(self, data: JSONDict, path: Path) -> ProjectFileMetadata:
        try:
            format_name = str(data["format_name"])
            schema_version = str(data["schema_version"])
            application_version = str(data["application_version"])
            created_at = datetime.fromisoformat(str(data["created_at"]))
            modified_at = datetime.fromisoformat(str(data["modified_at"]))
            if "project" not in data:
                raise KeyError("project")
        except (KeyError, ValueError) as exc:
            raise ProjectFileCorruptError(
                f"'{path}' no tiene la estructura esperada de un proyecto CargoOptimizer3D: {exc}"
            ) from exc

        if format_name != FORMAT_NAME:
            raise ProjectFileCorruptError(
                f"'{path}' declara el formato '{format_name}', no reconocido por CargoOptimizer3D."
            )
        _ensure_supported_schema_version(schema_version)

        return ProjectFileMetadata(
            format_name=format_name,
            schema_version=schema_version,
            application_version=application_version,
            created_at=created_at,
            modified_at=modified_at,
        )

    def _write_atomic(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            with suppress(OSError):
                os.remove(tmp_name)
            raise
