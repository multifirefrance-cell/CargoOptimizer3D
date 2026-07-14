"""Pruebas de UnpackedUnit."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit


def test_valid_creation() -> None:
    unit = UnpackedUnit(
        load_unit_id=uuid4(),
        instance_number=1,
        reason_code="NO_SPACE",
        reason_message="No cabe en el espacio restante.",
    )
    assert unit.reason_code == "NO_SPACE"


def test_invalid_instance_number_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        UnpackedUnit(
            load_unit_id=uuid4(),
            instance_number=0,
            reason_code="NO_SPACE",
            reason_message="No cabe.",
        )


def test_empty_reason_code_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        UnpackedUnit(
            load_unit_id=uuid4(),
            instance_number=1,
            reason_code="  ",
            reason_message="No cabe.",
        )


def test_empty_reason_message_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        UnpackedUnit(
            load_unit_id=uuid4(),
            instance_number=1,
            reason_code="NO_SPACE",
            reason_message="",
        )
