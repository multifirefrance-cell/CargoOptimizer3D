"""Validación de reglas de negocio no estructurales para un LoadUnit aislado."""

from __future__ import annotations

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.rules.extinguisher_rules import evaluate_extinguisher_configuration
from cargo_optimizer.rules.results import RuleEvaluation


def evaluate_load_unit_rules(load_unit: LoadUnit) -> RuleEvaluation:
    """Reglas de negocio sobre un LoadUnit aislado, sin contexto de colocación.

    No repite las invariantes ya garantizadas por
    `LoadUnit.__post_init__` (SKU no vacío, coherencia interna de los
    campos de extintor, etc.): solo añade recomendaciones de negocio,
    hoy limitadas a la capacidad recomendada de extintores en caja
    grupal (ver `extinguisher_rules.evaluate_extinguisher_configuration`).
    """
    return evaluate_extinguisher_configuration(load_unit)
