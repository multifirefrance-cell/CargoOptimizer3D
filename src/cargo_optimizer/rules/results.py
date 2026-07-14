"""Resultados del motor de reglas: RuleSeverity, RuleViolation y RuleEvaluation.

Estas estructuras son el vocabulario común de todo `cargo_optimizer.rules`:
cada regla devuelve un `RuleEvaluation` explícito, nunca lanza una
excepción para señalar que una colocación no es válida ni modifica
silenciosamente ninguna entidad de dominio.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class RuleSeverity(StrEnum):
    """Severidad de una `RuleViolation`. Valores estables (ver ADR-0005)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class RuleViolation:
    """Un problema concreto detectado por una regla."""

    code: str
    message: str
    severity: RuleSeverity
    load_unit_id: UUID | None = None
    placement_sequence_numbers: tuple[int, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("code no puede estar vacío.")
        if not self.message.strip():
            raise ValueError("message no puede estar vacío.")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    """Resultado de evaluar una o varias reglas: permitido o no, y el detalle.

    `is_allowed` es coherente por construcción con `violations`: nunca
    es `True` si existe alguna violación con `severity=error`. Se
    construye con `RuleEvaluation.allowed(...)`, `RuleEvaluation.rejected(...)`
    o `RuleEvaluation.combine(...)`, no directamente, para no romper esa
    coherencia por accidente.
    """

    is_allowed: bool
    violations: tuple[RuleViolation, ...]

    def __post_init__(self) -> None:
        if self.is_allowed and self.has_errors:
            raise ValueError(
                "is_allowed no puede ser True si existe una violación con severity=error."
            )

    @property
    def errors(self) -> tuple[RuleViolation, ...]:
        return tuple(v for v in self.violations if v.severity is RuleSeverity.ERROR)

    @property
    def warnings(self) -> tuple[RuleViolation, ...]:
        return tuple(v for v in self.violations if v.severity is RuleSeverity.WARNING)

    @property
    def info(self) -> tuple[RuleViolation, ...]:
        return tuple(v for v in self.violations if v.severity is RuleSeverity.INFO)

    @property
    def has_errors(self) -> bool:
        return any(v.severity is RuleSeverity.ERROR for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity is RuleSeverity.WARNING for v in self.violations)

    @classmethod
    def allowed(cls, violations: tuple[RuleViolation, ...] = ()) -> RuleEvaluation:
        """Resultado permitido; puede incluir advertencias o información, nunca errores."""
        return cls(is_allowed=True, violations=violations)

    @classmethod
    def rejected(cls, violations: tuple[RuleViolation, ...]) -> RuleEvaluation:
        """Resultado rechazado; requiere al menos una violación con severity=error."""
        if not any(v.severity is RuleSeverity.ERROR for v in violations):
            raise ValueError("rejected() requiere al menos una violación con severity=error.")
        return cls(is_allowed=False, violations=violations)

    @staticmethod
    def combine(evaluations: Sequence[RuleEvaluation]) -> RuleEvaluation:
        """Combina varias evaluaciones preservando el orden de entrada (determinista)."""
        all_violations = tuple(v for evaluation in evaluations for v in evaluation.violations)
        is_allowed = not any(v.severity is RuleSeverity.ERROR for v in all_violations)
        return RuleEvaluation(is_allowed=is_allowed, violations=all_violations)
