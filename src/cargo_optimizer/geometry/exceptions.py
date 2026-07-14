"""Jerarquía de excepciones del motor geométrico.

Deliberadamente pequeña, en el mismo espíritu que
``cargo_optimizer.domain.exceptions``: no se crea una excepción por
cada función.
"""

from __future__ import annotations


class GeometryError(Exception):
    """Raíz de cualquier error del motor geométrico."""


class GeometryValidationError(GeometryError):
    """Un argumento geométrico no cumple una invariante (p. ej. una ratio fuera de [0, 1])."""


class OutOfBoundsError(GeometryError):
    """Una caja no cabe dentro de los límites de un Loading Space."""
