"""Jerarquía de excepciones de `ProjectFileRepository`.

Cada caso que un llamador (`MainWindow`) necesita distinguir para
mostrar un mensaje distinto tiene su propia clase; nada más.
"""

from __future__ import annotations


class ProjectFileError(Exception):
    """Raíz de cualquier fallo al leer o escribir un archivo `.cargo3d`."""


class ProjectFileNotFoundError(ProjectFileError):
    """La ruta indicada no existe o no es un archivo."""


class ProjectFileCorruptError(ProjectFileError):
    """El archivo no es JSON válido, o le faltan campos requeridos del formato."""


class UnsupportedSchemaVersionError(ProjectFileError):
    """El archivo declara un `schema_version` que esta versión de la aplicación no sabe leer."""


class ProjectFileWriteError(ProjectFileError):
    """Fallo de E/S al escribir (incluida la copia de seguridad) un archivo `.cargo3d`."""
