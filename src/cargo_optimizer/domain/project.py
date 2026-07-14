"""CargoProject: agregado raíz que agrupa un Loading Space, sus Load Units y el último resultado."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from cargo_optimizer.domain.exceptions import DomainValidationError, DuplicateSkuError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult

_INITIAL_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class CargoProject:
    """Un proyecto de optimización: un Loading Space y el conjunto de Load Units a cargar."""

    name: str
    loading_space: LoadingSpace
    load_units: tuple[LoadUnit, ...] = ()
    latest_result: PackingResult | None = None
    notes: str = ""
    schema_version: str = _INITIAL_SCHEMA_VERSION
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("El nombre del proyecto no puede estar vacío.")
        seen_skus: set[str] = set()
        for unit in self.load_units:
            if unit.sku in seen_skus:
                raise DuplicateSkuError(f"SKU duplicado en el proyecto: '{unit.sku}'.")
            seen_skus.add(unit.sku)
