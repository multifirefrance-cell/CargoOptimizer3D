"""Jerarquía de excepciones de la capa de aplicación.

Pequeña y deliberada, mismo patrón que `domain.exceptions` y
`optimization.exceptions`.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Raíz de cualquier error de la capa de aplicación."""


class MultiSpaceAssignmentValidationError(ApplicationError):
    """Una `MultiSpaceAssignmentRequest` no cumple sus invariantes antes de ejecutar nada."""
