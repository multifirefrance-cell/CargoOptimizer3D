"""Jerarquía de excepciones de `infrastructure/database`.

Nunca se muestra un `QMessageBox` desde aquí: `presentation` decide
cómo informar al usuario, esta capa solo lanza errores tipados con
mensajes claros y conserva la causa original (`raise ... from exc`).
"""

from __future__ import annotations


class DatabaseError(Exception):
    """Raíz de cualquier fallo de la base de datos SQLite del catálogo/historial."""


class DatabaseInitializationError(DatabaseError):
    """La base no se pudo crear o abrir (ruta inválida, permisos, archivo dañado)."""


class DatabaseMigrationError(DatabaseError):
    """La base declara una `schema_version` que esta versión de la aplicación no reconoce."""


class RepositoryError(DatabaseError):
    """Fallo genérico de un repositorio (E/S, restricción violada, dato corrupto)."""


class DuplicateCatalogSkuError(RepositoryError):
    """Ya existe un producto activo del catálogo con ese SKU (sin distinguir mayúsculas)."""


class DuplicateLoadingSpaceProfileError(RepositoryError):
    """Ya existe un perfil de espacio activo con ese nombre (sin distinguir mayúsculas)."""


class DuplicateImportMappingProfileError(RepositoryError):
    """Ya existe un perfil de mapeo activo con ese nombre (sin distinguir mayúsculas)."""


class RecordNotFoundError(RepositoryError):
    """No existe ningún registro con el identificador solicitado."""
