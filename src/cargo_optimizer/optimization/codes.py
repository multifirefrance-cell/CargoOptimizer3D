"""Códigos estables para explicar por qué una instancia quedó sin colocar.

Estos códigos son la **causa final** a nivel de una instancia completa
(`PhysicalLoadInstance`), no las violaciones concretas de cada
candidato intentado (esas ya existen, con más detalle, en
`cargo_optimizer.rules.codes` — p. ej. `OUT_OF_BOUNDS`, `COLLISION`,
`UNSUPPORTED`). No se duplican aquí: `UnpackedReason` clasifica en un
puñado de categorías amplias, suficientes para decidir qué mensaje
mostrar a un usuario final; las violaciones finas quedan disponibles
para modo diagnóstico.
"""

from __future__ import annotations

from enum import StrEnum


class UnpackedReason(StrEnum):
    """Por qué el motor dejó de intentar colocar una instancia."""

    NO_VALID_ORIENTATION = "no_valid_orientation"
    NO_FEASIBLE_POSITION = "no_feasible_position"
    LOADING_SPACE_WEIGHT_EXCEEDED = "loading_space_weight_exceeded"
    TIME_LIMIT_REACHED = "time_limit_reached"
    ITERATION_LIMIT_REACHED = "iteration_limit_reached"
    CANCELLED = "cancelled"
    INVALID_INPUT = "invalid_input"
    INTERNAL_VALIDATION_FAILED = "internal_validation_failed"
