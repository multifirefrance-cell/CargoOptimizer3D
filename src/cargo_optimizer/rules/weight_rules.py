"""Reglas de peso total del Loading Space.

No calcula peso por ejes ni centro de gravedad: queda fuera de alcance
por decisión explícita (fase OPT-13, ver `docs/OptimizerPerformance.md`),
no es una limitación temporal. Solo el peso bruto total acumulado
frente al máximo declarado del Loading Space (obligatorio, nunca se
elimina).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.rules.codes import LOADING_SPACE_WEIGHT_EXCEEDED
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation

WEIGHT_TOLERANCE_KG = 1e-6
"""Tolerancia numérica para sumas de peso acumulado, en kilogramos.

Absorbe errores de redondeo de coma flotante al sumar muchos pesos; no
está pensada para permitir sobrepeso real (1e-6 kg es imperceptible en
cualquier báscula real). Antes de la fase OPT-13 vivía en
`stacking_rules` y se compartía con la (ya eliminada) regla de peso
soportado; ahora es exclusiva de esta regla, la única que queda.
"""


def current_loaded_weight_kg(
    existing_placements: Sequence[Placement],
    load_units_by_id: Mapping[UUID, LoadUnit],
) -> float:
    """Suma el peso bruto (`weight_kg`) de cada instancia física ya colocada.

    Los Placements que referencian un `load_unit_id` desconocido no
    suman peso (se tratan como 0 kg); esa inconsistencia se reporta por
    separado en `PlacementRuleContext.validate_placement_references`.
    """
    total = 0.0
    for placement in existing_placements:
        unit = load_units_by_id.get(placement.load_unit_id)
        if unit is not None:
            total += unit.weight_kg
    return total


def evaluate_loading_space_weight(context: PlacementRuleContext) -> RuleEvaluation:
    """Rechaza si el peso total (existente + candidato) supera `loading_space.max_weight_kg`."""
    max_weight = context.loading_space.max_weight_kg
    if max_weight is None:
        return RuleEvaluation.allowed()

    total = current_loaded_weight_kg(context.existing_placements, context.load_units_by_id)
    total += context.load_unit.weight_kg

    if total <= max_weight + WEIGHT_TOLERANCE_KG:
        return RuleEvaluation.allowed()

    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=LOADING_SPACE_WEIGHT_EXCEEDED,
                message=(
                    f"El peso total cargado sería {total:.3f} kg, por encima del máximo "
                    f"de '{context.loading_space.name}' ({max_weight:.3f} kg)."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
            ),
        )
    )
