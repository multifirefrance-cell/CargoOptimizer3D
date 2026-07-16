"""Capa de aplicación de CargoOptimizer3D.

Contiene los casos de uso (orquestación) y los puertos: interfaces que
``infrastructure`` deberá implementar (repositorios de persistencia,
exportadores de Excel/PDF, proveedores de visualización). Esta capa
decide *qué* pasos ejecuta el sistema, nunca *cómo* se guarda o se
dibuja algo, ni *dónde* coloca cada instancia un packing individual
(eso sigue siendo responsabilidad exclusiva de ``optimization``).

Regla de dependencia: depende de ``domain``, ``geometry``, ``rules`` y
``optimization``. Nunca importa ``infrastructure`` ni ``presentation``.

Primer caso de uso real (fase 10.1): ``MultiSpaceAssignmentEngine``,
que orquesta varias ejecuciones de ``PackingEngine.optimize(...)`` (una
por Loading Space) para responder "¿cuántos espacios hacen falta para
este pedido, y qué va en cada uno?" — ver
``docs/MultiSpaceAssignment.md``.
"""

from __future__ import annotations

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.exceptions import (
    ApplicationError,
    MultiSpaceAssignmentValidationError,
)
from cargo_optimizer.application.models import (
    MultiSpaceAssignmentRequest,
    MultiSpaceAssignmentResult,
    MultiSpaceProgress,
)
from cargo_optimizer.application.multi_space_assignment import MultiSpaceAssignmentEngine

__all__ = [
    "ApplicationError",
    "MultiSpaceAssignmentEngine",
    "MultiSpaceAssignmentRequest",
    "MultiSpaceAssignmentResult",
    "MultiSpaceAssignmentValidationError",
    "MultiSpaceProgress",
    "MultiSpaceStopReason",
]
