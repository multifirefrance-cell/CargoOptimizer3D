"""Jerarquía de excepciones de dominio.

Deliberadamente pequeña: una base y dos casos concretos. No se añaden
excepciones nuevas salvo que representen una regla de negocio distinta
que un llamador necesite distinguir explícitamente.
"""

from __future__ import annotations


class DomainError(Exception):
    """Raíz de cualquier violación de una regla de dominio."""


class DomainValidationError(DomainError):
    """Un valor no cumple una invariante de un value object o entidad."""


class DuplicateSkuError(DomainError):
    """Un CargoProject recibió más de un LoadUnit con el mismo SKU."""
