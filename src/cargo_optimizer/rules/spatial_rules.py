"""Reglas de límites, colisión y soporte.

No duplica lógica geométrica: delega siempre en
`cargo_optimizer.geometry`.
"""

from __future__ import annotations

from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.collision import boxes_overlap
from cargo_optimizer.geometry.support import is_supported
from cargo_optimizer.rules.codes import COLLISION, OUT_OF_BOUNDS, UNSUPPORTED
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation


def evaluate_bounds(context: PlacementRuleContext) -> RuleEvaluation:
    """Fuera de límites del Loading Space -> error."""
    if fits_inside_loading_space(context.candidate_box, context.loading_space):
        return RuleEvaluation.allowed()
    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=OUT_OF_BOUNDS,
                message=(
                    f"La colocación candidata de '{context.load_unit.sku}' queda fuera de "
                    f"los límites de '{context.loading_space.name}'."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
            ),
        )
    )


def evaluate_collision(context: PlacementRuleContext) -> RuleEvaluation:
    """Superposición con volumen positivo con cualquier Placement existente -> error.

    Tocar caras, aristas o vértices no es una colisión (ver
    `cargo_optimizer.geometry`, `overlaps` vs. `touches`).

    Cuando `context` trae un índice espacial precalculado, la
    comprobación exacta (`boxes_overlap`, sin cambios) solo se ejecuta
    contra el superconjunto barato que devuelve
    `context.nearby_sequence_numbers` — nunca contra todos los
    `existing_placements` (ver `rules/context.py` y
    `geometry/spatial_index.py`). Sin índice, el comportamiento es
    exactamente el de antes de esta fase.
    """
    candidate_box = context.candidate_box
    nearby = context.nearby_sequence_numbers
    candidates = (
        zip(context.existing_placements, context.existing_boxes, strict=True)
        if nearby is None
        else (
            (placement, box)
            for placement, box in zip(
                context.existing_placements, context.existing_boxes, strict=True
            )
            if placement.sequence_number in nearby
        )
    )
    colliding = [placement for placement, box in candidates if boxes_overlap(candidate_box, box)]
    if not colliding:
        return RuleEvaluation.allowed()
    return RuleEvaluation.rejected(
        tuple(
            RuleViolation(
                code=COLLISION,
                message=(
                    f"La colocación candidata de '{context.load_unit.sku}' colisiona con "
                    f"el Placement sequence_number={placement.sequence_number}."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
                placement_sequence_numbers=(placement.sequence_number,),
            )
            for placement in colliding
        )
    )


def evaluate_support(
    context: PlacementRuleContext,
    minimum_support_ratio: float = 1.0,
) -> RuleEvaluation:
    """Una caja en el suelo está soportada; por defecto se exige soporte completo.

    Usa `context.nearby_existing_boxes` (superconjunto barato vía
    índice espacial cuando está disponible, `existing_boxes` completo
    si no) en vez de recorrer siempre todas las cajas existentes — ver
    docstring de `evaluate_collision`.
    """
    if is_supported(
        context.candidate_box,
        context.nearby_existing_boxes,
        minimum_support_ratio=minimum_support_ratio,
    ):
        return RuleEvaluation.allowed()
    return RuleEvaluation.rejected(
        (
            RuleViolation(
                code=UNSUPPORTED,
                message=(
                    f"La colocación candidata de '{context.load_unit.sku}' no tiene "
                    "suficiente soporte."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=context.load_unit.id,
            ),
        )
    )
