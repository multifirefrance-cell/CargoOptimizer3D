"""Códigos estables del caso de uso de asignación multi-espacio.

Mismo criterio que `cargo_optimizer.optimization.codes`: un `StrEnum`
pequeño que explica, a nivel agregado, por qué terminó la asignación
de varios `LoadingSpace`, no por qué una instancia concreta no cargó
(eso ya lo explica `UnpackedReason`, reutilizado tal cual aquí).
"""

from __future__ import annotations

from enum import StrEnum


class MultiSpaceStopReason(StrEnum):
    """Por qué `MultiSpaceAssignmentEngine.assign(...)` dejó de añadir espacios."""

    ALL_PACKED = "all_packed"
    IMPOSSIBLE_REMAINING = "impossible_remaining"
    MAX_SPACES_REACHED = "max_spaces_reached"
    CANCELLED = "cancelled"
