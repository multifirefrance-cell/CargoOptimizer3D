"""Reglas de apilamiento.

Limitaciones conocidas de esta primera versión (evaluación
conservadora, ver Fase 3 del roadmap):

- `count_stack_level` no memoiza entre llamadas recursivas hermanas:
  para pilas muy profundas o muy ramificadas el coste puede crecer más
  de lo estrictamente necesario. Aceptable para los volúmenes de datos
  de esta fase; se documenta como candidato a optimizar si el
  optimizador (fase 4) lo requiere.
- No se asume que todos los elementos de una pila compartan SKU: cada
  nivel se calcula únicamente a partir de qué caja soporta físicamente
  a cuál, nunca por identidad de `LoadUnit`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.support import horizontal_overlap_area_cm2
from cargo_optimizer.rules.codes import MAX_STACK_EXCEEDED, SUPPORTED_WEIGHT_EXCEEDED
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.extinguisher_rules import effective_max_stack_count
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation

WEIGHT_TOLERANCE_KG = 1e-6
"""Tolerancia numérica para sumas de peso acumulado, en kilogramos.

Absorbe errores de redondeo de coma flotante al sumar muchos pesos; no
está pensada para permitir sobrepeso real (1e-6 kg es imperceptible en
cualquier báscula real). Compartida por `stacking_rules` y
`weight_rules` para no dispersar tolerancias distintas para el mismo
tipo de comparación.
"""

__all__ = [
    "WEIGHT_TOLERANCE_KG",
    "count_stack_level",
    "effective_max_stack_count",
    "evaluate_stack_count",
    "evaluate_supported_weight",
    "find_direct_supporting_placements",
]


def _box_of(
    placement: Placement, box_by_sequence_number: Mapping[int, AxisAlignedBox] | None
) -> AxisAlignedBox:
    """Caja de `placement`: O(1) si se conoce el mapa precalculado, si no recalcula igual que antes.

    Optimización de rendimiento pura (fase OPT-02): mismo resultado en
    ambos casos, `box_from_placement` es una función determinista de un
    `Placement` inmutable — ver `rules/context.py` y
    `docs/OptimizerPerformance.md`.
    """
    if box_by_sequence_number is not None:
        return box_by_sequence_number[placement.sequence_number]
    return box_from_placement(placement)


def find_direct_supporting_placements(
    candidate_box: AxisAlignedBox,
    existing_placements: Sequence[Placement],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
) -> tuple[Placement, ...]:
    """Placements cuya cara superior toca la base de `candidate_box` con solape positivo."""
    result: list[Placement] = []
    for placement in existing_placements:
        box = _box_of(placement, box_by_sequence_number)
        if abs(box.max_z - candidate_box.min_z) > GEOMETRY_EPSILON_CM:
            continue
        if horizontal_overlap_area_cm2(candidate_box, box) <= GEOMETRY_EPSILON_CM:
            continue
        result.append(placement)
    return tuple(result)


def count_stack_level(
    candidate_box: AxisAlignedBox,
    existing_placements: Sequence[Placement],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
) -> int:
    """Nivel de apilamiento de `candidate_box` sobre `existing_placements`.

    Convención (documentada explícitamente, ver módulo): una caja en el
    suelo está en nivel 1. Una caja apoyada directamente sobre una o
    más cajas está en `1 + max(nivel de cada soporte directo)` — la
    convención más restrictiva cuando el soporte proviene de cajas a
    niveles distintos.
    """
    if candidate_box.min_z <= GEOMETRY_EPSILON_CM:
        return 1

    supporters = find_direct_supporting_placements(
        candidate_box, existing_placements, box_by_sequence_number
    )
    if not supporters:
        return 1

    levels = [
        count_stack_level(
            _box_of(supporter, box_by_sequence_number),
            existing_placements,
            box_by_sequence_number,
        )
        for supporter in supporters
    ]
    return 1 + max(levels)


def evaluate_stack_count(context: PlacementRuleContext) -> RuleEvaluation:
    """Rechaza la candidata si su nivel de apilamiento supera el máximo efectivo."""
    max_allowed = effective_max_stack_count(context.load_unit)
    level = count_stack_level(
        context.candidate_box, context.existing_placements, context.box_by_sequence_number
    )
    if level <= max_allowed:
        return RuleEvaluation.allowed()
    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=MAX_STACK_EXCEEDED,
                message=(
                    f"'{context.load_unit.sku}' alcanzaría el nivel de apilamiento {level}, "
                    f"por encima del máximo efectivo {max_allowed}."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
            ),
        )
    )


def _weight_resting_on(
    placement: Placement,
    existing_placements: Sequence[Placement],
    load_units_by_id: Mapping[UUID, LoadUnit],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
) -> float:
    """Peso total (recursivo) que actualmente descansa encima de `placement`.

    Evaluación conservadora: recorre todas las cajas existentes en
    busca de las que se apoyan, directa o indirectamente, en
    `placement`. No distribuye el peso proporcionalmente entre varios
    soportes: cada caja aporta su peso completo a cada uno de sus
    soportes directos (ver limitaciones del módulo).
    """
    total = 0.0
    for other in existing_placements:
        if other is placement:
            continue
        other_box = _box_of(other, box_by_sequence_number)
        supporters = find_direct_supporting_placements(
            other_box, existing_placements, box_by_sequence_number
        )
        if placement in supporters:
            other_unit = load_units_by_id.get(other.load_unit_id)
            other_weight = other_unit.weight_kg if other_unit is not None else 0.0
            total += other_weight + _weight_resting_on(
                other, existing_placements, load_units_by_id, box_by_sequence_number
            )
    return total


def _all_transitive_supporters(
    candidate_box: AxisAlignedBox,
    existing_placements: Sequence[Placement],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
) -> list[Placement]:
    """Todos los Placements que soportan, directa o transitivamente, a `candidate_box`.

    Necesario porque añadir peso a una caja afecta también a todo lo que
    la sostiene por debajo, no solo a su soporte directo: si A soporta a
    B y B soporta a la candidata, el límite de `max_supported_weight_kg`
    de A también debe comprobarse.
    """
    supporters: list[Placement] = []
    seen_sequence_numbers: set[int] = set()
    pending = list(
        find_direct_supporting_placements(
            candidate_box, existing_placements, box_by_sequence_number
        )
    )
    while pending:
        supporter = pending.pop()
        if supporter.sequence_number in seen_sequence_numbers:
            continue
        seen_sequence_numbers.add(supporter.sequence_number)
        supporters.append(supporter)
        pending.extend(
            find_direct_supporting_placements(
                _box_of(supporter, box_by_sequence_number),
                existing_placements,
                box_by_sequence_number,
            )
        )
    return supporters


def evaluate_supported_weight(context: PlacementRuleContext) -> RuleEvaluation:
    """Rechaza si algún soporte, directo o transitivo, excedería su `max_supported_weight_kg`."""
    box_by_sequence_number = context.box_by_sequence_number
    supporters = _all_transitive_supporters(
        context.candidate_box, context.existing_placements, box_by_sequence_number
    )
    violations: list[RuleViolation] = []
    for supporter in supporters:
        supporter_unit = context.load_units_by_id.get(supporter.load_unit_id)
        if supporter_unit is None or supporter_unit.max_supported_weight_kg is None:
            continue
        existing_weight = _weight_resting_on(
            supporter, context.existing_placements, context.load_units_by_id, box_by_sequence_number
        )
        total_weight = existing_weight + context.load_unit.weight_kg
        if total_weight > supporter_unit.max_supported_weight_kg + WEIGHT_TOLERANCE_KG:
            violations.append(
                RuleViolation(
                    code=SUPPORTED_WEIGHT_EXCEEDED,
                    message=(
                        f"El Placement sequence_number={supporter.sequence_number} "
                        f"('{supporter_unit.sku}') soportaría {total_weight:.3f} kg, por "
                        f"encima de su máximo {supporter_unit.max_supported_weight_kg:.3f} kg."
                    ),
                    severity=RuleSeverity.ERROR,
                    load_unit_id=supporter_unit.id,
                    placement_sequence_numbers=(supporter.sequence_number,),
                )
            )
    if violations:
        return RuleEvaluation.rejected(tuple(violations))
    return RuleEvaluation.allowed()
