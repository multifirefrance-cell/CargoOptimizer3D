"""UnpackedUnit: instancia de un Load Unit que no pudo colocarse en el Loading Space."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cargo_optimizer.domain.exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class UnpackedUnit:
    """Registra por qué una instancia concreta de un LoadUnit quedó sin cargar."""

    load_unit_id: UUID
    instance_number: int
    reason_code: str
    reason_message: str

    def __post_init__(self) -> None:
        if self.instance_number < 1:
            raise DomainValidationError("instance_number debe ser mayor o igual que 1.")
        if not self.reason_code.strip():
            raise DomainValidationError("reason_code no puede estar vacío.")
        if not self.reason_message.strip():
            raise DomainValidationError("reason_message no puede estar vacío.")
