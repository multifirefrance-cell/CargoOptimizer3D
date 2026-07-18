"""Reglas de apilamiento.

Alcance (fase OPT-13, ver `docs/OptimizerPerformance.md`): este módulo
solo controla el **número máximo de niveles** permitido por SKU
(`LoadUnit.max_stack_count`, respetado tal cual para cualquier
producto — ver "Fase OPT-15" en `docs/OptimizerPerformance.md`: no
existe ninguna excepción automática por tipo de producto, incluidos
los extintores). No calcula peso soportado acumulado ni
propaga peso entre cajas — esa capacidad se eliminó por completo (no
solo se optimizó) en esta fase, junto con la recursión no acotada que
implicaba (antes, `count_stack_level` recorría la cadena de soporte
hacia arriba en cada evaluación; `_weight_resting_on`/
`_all_transitive_supporters` recorrían la estructura completa de cajas
para acumular peso). No implementa peso por eje ni centro de gravedad;
queda fuera de alcance, no es una limitación temporal.

El cálculo del nivel de apilamiento en sí (no recursivo) vive en
`rules.stack_levels`, un módulo hoja que tanto este módulo como
`rules.context.PlacementRuleContext` pueden importar sin crear un
ciclo. El nivel de cada `Placement` ya aceptado se calcula una única
vez, de forma incremental, en `PackingState.accept_placement`
(`optimization/state.py`): al aceptar una caja, su nivel es `1` si está
en el suelo o `1 + max(nivel ya conocido de cada soporte directo)` —
los soportes directos, al haberse aceptado antes, ya tienen su nivel
calculado, así que nunca hace falta volver a subir por la cadena.
`evaluate_stack_count` consulta ese nivel ya calculado (vía
`PlacementRuleContext.stack_level_by_sequence_number`); cuando no se
proporciona un mapa precalculado (el caso de toda prueba unitaria que
construye un `PlacementRuleContext` a mano), se calcula en una única
pasada lineal (`rules.stack_levels.compute_stack_levels`), tampoco
recursiva.

No se asume que todos los elementos de una pila compartan SKU: cada
nivel se calcula únicamente a partir de qué caja soporta físicamente a
cuál, nunca por identidad de `LoadUnit`.
"""

from __future__ import annotations

from cargo_optimizer.rules.codes import MAX_STACK_EXCEEDED
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation
from cargo_optimizer.rules.stack_levels import (
    compute_stack_levels,
    find_direct_supporting_placements,
    stack_level_of,
)

__all__ = [
    "compute_stack_levels",
    "evaluate_stack_count",
    "find_direct_supporting_placements",
    "stack_level_of",
]


def evaluate_stack_count(context: PlacementRuleContext) -> RuleEvaluation:
    """Rechaza la candidata si su nivel de apilamiento supera `load_unit.max_stack_count`.

    Sin excepciones por tipo de producto: todo `LoadUnit`, incluidos los
    extintores, se limita exclusivamente por el valor configurado en su
    propio SKU (ver "Fase OPT-15", `docs/OptimizerPerformance.md`).
    """
    max_allowed = context.load_unit.max_stack_count
    supporters = find_direct_supporting_placements(
        context.candidate_box,
        context.existing_placements,
        context.box_by_sequence_number,
        context.precomputed_spatial_index,
    )
    level = stack_level_of(
        context.candidate_box, supporters, context.stack_level_by_sequence_number
    )
    if level <= max_allowed:
        return RuleEvaluation.allowed()
    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=MAX_STACK_EXCEEDED,
                message=(
                    f"'{context.load_unit.sku}' alcanzaría el nivel de apilamiento {level}, "
                    f"por encima del máximo permitido {max_allowed}."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
            ),
        )
    )
