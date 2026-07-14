"""Motor de reglas de negocio de CargoOptimizer3D.

Responde preguntas sobre validez de una configuración o colocación —
¿qué orientaciones están permitidas?, ¿puede colocarse esta unidad
aquí?, ¿puede apilarse sobre esta otra?, ¿qué advertencias o errores
genera una colocación? — sin decidir dónde colocar nada: eso es
responsabilidad del futuro motor de optimización (fase 4).

Regla de dependencia: depende siempre de `domain`, y de `geometry`
únicamente donde una regla necesita información espacial (límites,
colisión, soporte). Nunca depende de `application`, `infrastructure`
ni `presentation`, ni de ninguna biblioteca externa. Verificado por
import-linter (ver ADR-0007).
"""

from __future__ import annotations

from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.engine import RulesEngine
from cargo_optimizer.rules.orientation_rules import allowed_orientations_for_load_unit
from cargo_optimizer.rules.placement_rules import evaluate_candidate_placement
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation
from cargo_optimizer.rules.stacking_rules import effective_max_stack_count

__all__ = [
    "PlacementRuleContext",
    "RuleEvaluation",
    "RuleSeverity",
    "RuleViolation",
    "RulesEngine",
    "allowed_orientations_for_load_unit",
    "effective_max_stack_count",
    "evaluate_candidate_placement",
]
