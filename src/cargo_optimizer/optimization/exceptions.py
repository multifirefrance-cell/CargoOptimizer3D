"""Jerarquía de excepciones del motor de optimización.

Pequeña y deliberada, mismo patrón que `domain.exceptions`,
`geometry.exceptions` y las excepciones internas de `rules`. Nunca se
lanza una excepción porque una instancia no quepa: eso es siempre un
`UnpackedUnit` (ver `codes.py`).
"""

from __future__ import annotations


class OptimizationError(Exception):
    """Raíz de cualquier error del motor de optimización."""


class PackingRequestValidationError(OptimizationError):
    """Una `PackingRequest` no cumple sus invariantes antes de ejecutar nada."""


class OptimizationInternalError(OptimizationError):
    """El motor produjo un resultado internamente inconsistente.

    Indica un bug del propio motor (p. ej. la validación final del
    layout detecta una colisión entre placements ya aceptados), nunca
    una limitación esperada como "esta caja no cupo".
    """
