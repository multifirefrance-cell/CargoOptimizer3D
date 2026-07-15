"""Fachada del motor de optimización: único punto de entrada público."""

from __future__ import annotations

from collections.abc import Callable

from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.layout_validation import validate_layout
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.exceptions import OptimizationInternalError
from cargo_optimizer.optimization.greedy_extreme_point import GreedyExtremePointStrategy
from cargo_optimizer.optimization.models import PackingProgress, PackingRequest
from cargo_optimizer.optimization.strategy import PackingStrategy
from cargo_optimizer.rules.engine import RulesEngine


class PackingEngine:
    """Punto de entrada único del motor. Sin estado propio salvo la estrategia elegida.

    ``engine = PackingEngine()`` usa `GreedyExtremePointStrategy` por
    defecto; ``engine = PackingEngine(strategy=...)`` permite sustituir
    la estrategia por cualquier objeto compatible con el `Protocol
    PackingStrategy`. Sin registro dinámico ni sistema de plugins (ver
    ADR-0008): añadir una nueva estrategia es, hoy, pasarla
    explícitamente al constructor.
    """

    def __init__(self, strategy: PackingStrategy | None = None) -> None:
        self._strategy: PackingStrategy = strategy or GreedyExtremePointStrategy()

    def optimize(
        self,
        request: PackingRequest,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[PackingProgress], None] | None = None,
    ) -> PackingResult:
        """Ejecuta la estrategia configurada y valida el layout resultante antes de devolverlo."""
        rules_engine = RulesEngine()
        token = cancellation_token if cancellation_token is not None else CancellationToken()

        result = self._strategy.pack(request, rules_engine, token, progress_callback)

        # Si la solicitud pidió soporte parcial (`minimum_support_ratio` < 1.0), la
        # validación final no puede exigir soporte completo: contradeciría lo que el
        # propio motor aceptó intencionadamente al empaquetar. Límites, colisiones y
        # duplicados sí se comprueban siempre: ninguna colocación aceptada debería
        # violarlos jamás, sea cual sea el ratio de soporte solicitado.
        require_full_support = request.minimum_support_ratio >= 1.0 - GEOMETRY_EPSILON_CM
        validation = validate_layout(
            request.loading_space,
            result.placements,
            require_full_support=require_full_support,
        )
        if validation.is_valid:
            return result

        details = "; ".join(f"{issue.code}: {issue.message}" for issue in validation.issues)
        raise OptimizationInternalError(
            "La validación final del layout detectó una inconsistencia interna del "
            f"motor (esto indica un bug, no una limitación esperada): {details}"
        )
