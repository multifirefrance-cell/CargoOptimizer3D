"""Reglas de fragilidad: nada puede apoyarse sobre una LoadUnit frágil.

No implementa todavía categorías de fragilidad (p. ej. distintos
niveles de sensibilidad): solo el booleano `LoadUnit.fragile`.
"""

from __future__ import annotations

from cargo_optimizer.rules.codes import FRAGILE_SUPPORT
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation
from cargo_optimizer.rules.stacking_rules import find_direct_supporting_placements


def evaluate_fragility(context: PlacementRuleContext) -> RuleEvaluation:
    """Rechaza la candidata si se apoya, total o parcialmente, en una LoadUnit frágil.

    Usa soporte físico real (`find_direct_supporting_placements`, que a
    su vez exige contacto de altura y solape horizontal positivo), no
    una coincidencia aproximada de X/Y: una caja frágil puede estar
    junto a otra sin que eso implique que la soporta. Una LoadUnit
    frágil sí puede colocarse *sobre* otra (esta regla solo restringe
    qué se coloca encima de ella, no dónde se coloca ella misma).
    """
    supporters = find_direct_supporting_placements(
        context.candidate_box, context.existing_placements
    )
    violations = [
        RuleViolation(
            code=FRAGILE_SUPPORT,
            message=(
                f"No puede colocarse nada sobre el Placement sequence_number="
                f"{supporter.sequence_number} ('{supporter_unit.sku}'), marcado como frágil."
            ),
            severity=RuleSeverity.ERROR,
            load_unit_id=supporter_unit.id,
            placement_sequence_numbers=(supporter.sequence_number,),
        )
        for supporter in supporters
        if (supporter_unit := context.load_units_by_id.get(supporter.load_unit_id)) is not None
        and supporter_unit.fragile
    ]
    if violations:
        return RuleEvaluation.rejected(tuple(violations))
    return RuleEvaluation.allowed()
