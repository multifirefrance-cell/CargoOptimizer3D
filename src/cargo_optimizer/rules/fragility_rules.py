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

    Fase OPT-16 (ver `docs/OptimizerPerformance.md`): antes de esta
    fase, esta llamada no pasaba ni el índice espacial ni los mapas
    precalculados de `context` — pese a que `PackingState` ya los
    mantenía incrementalmente para el resto de reglas espaciales
    (colisión, soporte, apilamiento). El efecto real: cada candidato
    evaluado reconstruía `AxisAlignedBox` desde cero
    (`box_from_placement`) para **todos** los `Placement` existentes,
    sin excepción, fuera cual fuera el tamaño real del vecindario
    geométrico — el cuello de botella dominante medido en el caso real
    de 2000 unidades (~50 min para 1397 cargadas). Con estos argumentos,
    el recorrido se acota al mismo subconjunto barato que ya usan
    `evaluate_collision`/`evaluate_support`/`evaluate_stack_count`.
    """
    supporters = find_direct_supporting_placements(
        context.candidate_box,
        context.existing_placements,
        context.box_by_sequence_number,
        context.precomputed_spatial_index,
        context.precomputed_placement_by_sequence_number,
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
