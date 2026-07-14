"""Pruebas de RuleSeverity, RuleViolation y RuleEvaluation."""

from __future__ import annotations

import pytest

from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation


def _violation(severity: RuleSeverity, code: str = "TEST_CODE") -> RuleViolation:
    return RuleViolation(code=code, message="mensaje de prueba", severity=severity)


def test_allowed_without_violations() -> None:
    evaluation = RuleEvaluation.allowed()
    assert evaluation.is_allowed
    assert evaluation.violations == ()
    assert not evaluation.has_errors
    assert not evaluation.has_warnings


def test_rejected_by_error() -> None:
    violation = _violation(RuleSeverity.ERROR)
    evaluation = RuleEvaluation.rejected((violation,))
    assert not evaluation.is_allowed
    assert evaluation.has_errors
    assert evaluation.errors == (violation,)


def test_warning_does_not_reject() -> None:
    violation = _violation(RuleSeverity.WARNING)
    evaluation = RuleEvaluation.allowed((violation,))
    assert evaluation.is_allowed
    assert evaluation.has_warnings
    assert not evaluation.has_errors
    assert evaluation.warnings == (violation,)


def test_rejected_requires_an_error() -> None:
    with pytest.raises(ValueError, match="severity=error"):
        RuleEvaluation.rejected((_violation(RuleSeverity.WARNING),))


def test_direct_construction_rejects_inconsistent_state() -> None:
    with pytest.raises(ValueError):
        RuleEvaluation(is_allowed=True, violations=(_violation(RuleSeverity.ERROR),))


def test_combine_evaluations() -> None:
    e1 = RuleEvaluation.allowed((_violation(RuleSeverity.INFO, "A"),))
    e2 = RuleEvaluation.rejected((_violation(RuleSeverity.ERROR, "B"),))
    combined = RuleEvaluation.combine([e1, e2])
    assert not combined.is_allowed
    assert [v.code for v in combined.violations] == ["A", "B"]


def test_combine_order_is_deterministic() -> None:
    e1 = RuleEvaluation.allowed((_violation(RuleSeverity.INFO, "A"),))
    e2 = RuleEvaluation.allowed((_violation(RuleSeverity.WARNING, "B"),))
    e3 = RuleEvaluation.allowed((_violation(RuleSeverity.INFO, "C"),))
    combined_1 = RuleEvaluation.combine([e1, e2, e3])
    combined_2 = RuleEvaluation.combine([e1, e2, e3])
    assert combined_1 == combined_2
    assert [v.code for v in combined_1.violations] == ["A", "B", "C"]


def test_metadata_is_immutable() -> None:
    violation = RuleViolation(
        code="TEST",
        message="mensaje",
        severity=RuleSeverity.INFO,
        metadata={"key": "value"},
    )
    with pytest.raises(TypeError):
        violation.metadata["key"] = "otro"  # type: ignore[index]


def test_empty_code_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuleViolation(code="  ", message="mensaje", severity=RuleSeverity.ERROR)


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuleViolation(code="CODE", message="", severity=RuleSeverity.ERROR)
