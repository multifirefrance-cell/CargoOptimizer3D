"""Reglas de orientaciones permitidas para un LoadUnit.

No comprueba todavía colisiones ni límites: esa combinación ocurre en
`placement_rules.evaluate_candidate_placement`.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.rules.codes import ORIENTATION_NOT_ALLOWED
from cargo_optimizer.rules.extinguisher_rules import (
    evaluate_extinguisher_orientation,
    is_individual_large_extinguisher,
)
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation


def _dedupe_geometrically(orientations: tuple[Orientation, ...]) -> tuple[Orientation, ...]:
    seen_dims: list[Dimensions3D] = []
    unique: list[Orientation] = []
    for orientation in orientations:
        if orientation.dimensions not in seen_dims:
            seen_dims.append(orientation.dimensions)
            unique.append(orientation)
    return tuple(unique)


def allowed_orientations_for_load_unit(
    load_unit: LoadUnit,
    loading_space: LoadingSpace,
) -> tuple[Orientation, ...]:
    """Orientaciones geométricamente distintas permitidas para este LoadUnit.

    Parte de `load_unit.candidate_orientations()` (que ya deduplica por
    `OrientationCode`), elimina además las orientaciones cuyas
    `Dimensions3D` resultantes coinciden (p. ej. cuando dos dimensiones
    originales son iguales, dos códigos distintos producen la misma
    caja), mantiene un orden determinista, y aplica las reglas
    especiales de extintores: para un extintor individual >= 3 kg, solo
    quedan las orientaciones que dejan `length_cm` sobre X. No
    comprueba todavía colisiones ni límites.
    """
    candidates = _dedupe_geometrically(load_unit.candidate_orientations())
    if not is_individual_large_extinguisher(load_unit):
        return candidates
    return tuple(
        orientation
        for orientation in candidates
        if evaluate_extinguisher_orientation(load_unit, loading_space, orientation).is_allowed
    )


def evaluate_orientation(
    load_unit: LoadUnit,
    loading_space: LoadingSpace,
    orientation: Orientation,
) -> RuleEvaluation:
    """Evalúa si `orientation` es válida para `load_unit` en `loading_space`.

    Combina la regla de extintores (si aplica) con la comprobación de
    que el código esté entre los declarados en
    `load_unit.allowed_orientation_codes`.
    """
    extinguisher_result = evaluate_extinguisher_orientation(load_unit, loading_space, orientation)
    if not extinguisher_result.is_allowed:
        return extinguisher_result

    if orientation.code not in load_unit.allowed_orientation_codes:
        return RuleEvaluation.rejected(
            (
                RuleViolation(
                    code=ORIENTATION_NOT_ALLOWED,
                    message=(
                        f"La orientación {orientation.code.value} no está en "
                        f"allowed_orientation_codes de '{load_unit.sku}'."
                    ),
                    severity=RuleSeverity.ERROR,
                    load_unit_id=load_unit.id,
                ),
            )
        )
    return RuleEvaluation.allowed()
