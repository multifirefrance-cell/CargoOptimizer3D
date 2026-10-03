"""Reglas de orientaciones permitidas para un LoadUnit.

No comprueba todavía colisiones ni límites: esa combinación ocurre en
`placement_rules.evaluate_candidate_placement`.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
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

    Para extintores individuales >= 3 kg se expanden automáticamente los
    candidatos a los 6 códigos posibles (independientemente de los códigos
    almacenados en el catálogo) y la regla de extintores filtra la única
    orientación no permitida: la vertical (eje longitudinal sobre Z). El
    resultado son exactamente dos orientaciones distintas por simetría:
    la **paralela** (eje largo sobre X) y la **perpendicular** (eje largo
    sobre Y). La orientación paralela puntúa más en ``select_preferred_orientation``
    para contenedores estándar, por lo que se elige en la ronda 1; la
    perpendicular queda disponible en la ronda 2 para llenar el hueco
    residual al final del contenedor cuando el espacio paralelo se agota.

    Para cualquier otro LoadUnit se usa ``candidate_orientations()`` tal
    como está en el catálogo, eliminando duplicados geométricos.
    No comprueba colisiones ni límites (eso ocurre en
    `placement_rules.evaluate_candidate_placement`).
    """
    if is_individual_large_extinguisher(load_unit):
        all_six = _dedupe_geometrically(
            tuple(
                Orientation.from_base_dimensions(load_unit.dimensions, code)
                for code in OrientationCode
            )
        )
        return tuple(
            o for o in all_six
            if evaluate_extinguisher_orientation(load_unit, loading_space, o).is_allowed
        )

    candidates = _dedupe_geometrically(load_unit.candidate_orientations())
    return candidates


def evaluate_orientation(
    load_unit: LoadUnit,
    loading_space: LoadingSpace,
    orientation: Orientation,
) -> RuleEvaluation:
    """Evalúa si `orientation` es válida para `load_unit` en `loading_space`.

    Combina la regla de extintores (si aplica) con la comprobación de
    que el código esté entre los declarados en
    `load_unit.allowed_orientation_codes`.

    Para extintores individuales grandes, `allowed_orientations_for_load_unit`
    ya ignora `allowed_orientation_codes` y usa exclusivamente la regla de
    extintor (horizontal/vertical). El chequeo de códigos se omite aquí para
    que ambas funciones sean consistentes: el deduplicador geométrico puede
    elegir `lhw_xyz` como representante de la clase {whl_xyz, lhw_xyz} aunque
    solo `whl_xyz` esté en `allowed_orientation_codes`.
    """
    extinguisher_result = evaluate_extinguisher_orientation(load_unit, loading_space, orientation)
    if not extinguisher_result.is_allowed:
        return extinguisher_result

    if is_individual_large_extinguisher(load_unit):
        return RuleEvaluation.allowed()

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
