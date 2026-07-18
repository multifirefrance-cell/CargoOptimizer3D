"""Fachada del motor de reglas: punto de entrada único para el futuro optimizador.

`RulesEngine` no mantiene estado mutable: cada método delega en una
función pura del módulo correspondiente. No hay sistema de plugins,
registro dinámico de reglas ni reflection — ver docs/RulesEngine.md
para por qué esto es deliberado en esta fase.
"""

from __future__ import annotations

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.load_unit_rules import evaluate_load_unit_rules
from cargo_optimizer.rules.orientation_rules import allowed_orientations_for_load_unit
from cargo_optimizer.rules.placement_rules import evaluate_candidate_placement
from cargo_optimizer.rules.results import RuleEvaluation


class RulesEngine:
    """Fachada sin estado sobre las funciones de `cargo_optimizer.rules`."""

    def allowed_orientations(
        self, load_unit: LoadUnit, loading_space: LoadingSpace
    ) -> tuple[Orientation, ...]:
        return allowed_orientations_for_load_unit(load_unit, loading_space)

    def evaluate_load_unit(self, load_unit: LoadUnit) -> RuleEvaluation:
        return evaluate_load_unit_rules(load_unit)

    def evaluate_placement(
        self, context: PlacementRuleContext, minimum_support_ratio: float = 1.0
    ) -> RuleEvaluation:
        return evaluate_candidate_placement(context, minimum_support_ratio=minimum_support_ratio)
