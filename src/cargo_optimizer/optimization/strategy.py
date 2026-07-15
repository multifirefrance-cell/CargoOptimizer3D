"""Contrato de estrategia de empaquetado.

`PackingStrategy` es un `Protocol` (PEP 544), no una `ABC`: no existe
todavía comportamiento compartido real entre estrategias que
justifique una jerarquía de clases con métodos concretos heredados
(ver ADR-0008). Cualquier clase con los atributos/métodos correctos lo
satisface, sin necesidad de heredar de nada de este paquete.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.models import PackingProgress, PackingRequest
from cargo_optimizer.rules.engine import RulesEngine


@dataclass(frozen=True, slots=True)
class StrategyCapabilities:
    """Metadatos que `PackingEngine` puede inspeccionar antes de ejecutar una estrategia."""

    is_deterministic: bool
    supports_cancellation: bool
    supports_time_limit: bool


class PackingStrategy(Protocol):
    """Contrato que debe cumplir cualquier algoritmo de empaquetado intercambiable."""

    name: str

    def capabilities(self) -> StrategyCapabilities: ...

    def pack(
        self,
        request: PackingRequest,
        rules_engine: RulesEngine,
        cancellation_token: CancellationToken,
        progress_callback: Callable[[PackingProgress], None] | None,
    ) -> PackingResult: ...
