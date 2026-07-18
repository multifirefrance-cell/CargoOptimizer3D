"""Regla compuesta de colocación: combina todas las evaluaciones parciales en un único resultado.

Política de evaluación (ver docs/RulesEngine.md): se ejecutan siempre
la configuración de extintor, la orientación, los límites, la colisión
y el peso máximo del espacio. Soporte, apilamiento y fragilidad se
omiten cuando ya hay colisión: las tres dependen de "qué soporta
físicamente a la candidata", una pregunta sin respuesta consistente
cuando la candidata ocupa un volumen ya en disputa con otra caja.
Omitirlas evita una cascada de errores irrelevantes derivados
únicamente de la colisión, sin dejar de reportar límites, orientación o
peso, que son independientes de si el volumen está disputado.
"""

from __future__ import annotations

from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.extinguisher_rules import evaluate_extinguisher_configuration
from cargo_optimizer.rules.fragility_rules import evaluate_fragility
from cargo_optimizer.rules.orientation_rules import evaluate_orientation
from cargo_optimizer.rules.results import RuleEvaluation
from cargo_optimizer.rules.spatial_rules import (
    evaluate_bounds,
    evaluate_collision,
    evaluate_support,
)
from cargo_optimizer.rules.stacking_rules import evaluate_stack_count
from cargo_optimizer.rules.weight_rules import evaluate_loading_space_weight


def evaluate_candidate_placement(
    context: PlacementRuleContext,
    minimum_support_ratio: float = 1.0,
) -> RuleEvaluation:
    """Evalúa una colocación candidata combinando las 8 reglas, en orden determinista.

    1. configuración de extintor
    2. orientación
    3. límites
    4. colisión
    5. soporte (omitida si hay colisión)
    6. apilamiento (omitida si hay colisión)
    7. fragilidad (omitida si hay colisión)
    8. peso máximo del LoadingSpace

    No se detiene en la primera violación: devuelve todas las
    detectables razonablemente, salvo la excepción documentada arriba.
    """
    evaluations = [
        evaluate_extinguisher_configuration(context.load_unit),
        evaluate_orientation(
            context.load_unit, context.loading_space, context.candidate_orientation
        ),
        evaluate_bounds(context),
        evaluate_collision(context),
    ]

    collision_is_clear = evaluations[-1].is_allowed
    if collision_is_clear:
        evaluations.append(evaluate_support(context, minimum_support_ratio=minimum_support_ratio))
        evaluations.append(evaluate_stack_count(context))
        evaluations.append(evaluate_fragility(context))

    evaluations.append(evaluate_loading_space_weight(context))

    return RuleEvaluation.combine(evaluations)
