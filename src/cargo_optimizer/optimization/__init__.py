"""Motor de optimización de CargoOptimizer3D.

Recibe un `LoadingSpace` y una colección de `LoadUnit`, expande
cantidades en instancias físicas, genera y evalúa candidatos de
colocación usando `cargo_optimizer.geometry` y
`cargo_optimizer.rules`, y produce un `PackingResult`. Decide dónde
colocar cada instancia; nunca decide si una colocación es válida (eso
ya lo resuelve `rules`) ni cómo calcular geometría (eso ya lo resuelve
`geometry`).

Regla de dependencia: depende de `domain`, `geometry` y `rules`. Nunca
depende de `application`, `infrastructure`, `presentation` ni de
ninguna biblioteca externa. Verificado por import-linter (ver
ADR-0008).

Primera estrategia implementada: `greedy_extreme_point_v1`
(`GreedyExtremePointStrategy`), determinista, ver
docs/OptimizationEngine.md.
"""

from __future__ import annotations

from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.greedy_extreme_point import GreedyExtremePointStrategy
from cargo_optimizer.optimization.models import PackingProgress, PackingRequest

__all__ = [
    "CancellationToken",
    "GreedyExtremePointStrategy",
    "PackingEngine",
    "PackingProgress",
    "PackingRequest",
]
