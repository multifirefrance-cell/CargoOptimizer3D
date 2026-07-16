"""MultiSpaceAssignmentEngine: asignación automática de múltiples Loading Space.

Primer caso de uso real de la capa `application` (ver ADR-0001 y
`docs/Architecture.md`): orquesta varias ejecuciones de
`PackingEngine.optimize(...)` (una por espacio), nunca reimplementa
búsqueda de colocación — eso sigue siendo responsabilidad exclusiva de
`optimization`. Responde la pregunta que `PackingEngine` por sí solo no
puede responder: "¿cuántos Loading Space hacen falta para este pedido,
y qué va en cada uno?".

Algoritmo determinista, sin búsqueda combinatoria (mismo espíritu que
ADR-0008/ADR-0009): para cada espacio nuevo que haga falta, se ejecuta
el `PackingEngine` sobre **todos** los `loading_space_candidates` de la
solicitud y se elige, determinísticamente, el mejor resultado de esa
ronda — ver `_select_best_candidate` para el criterio exacto de
comparación. Minimizar estrictamente el número de espacios usados es
NP-duro y queda fuera de alcance; elegir el mejor resultado ronda a
ronda (en vez de buscar combinaciones completas) es una aproximación
razonable y ya es la práctica del resto del motor.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.models import (
    MultiSpaceAssignmentRequest,
    MultiSpaceAssignmentResult,
    MultiSpaceProgress,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.engine import PackingEngine

_STOP_REASON_MESSAGES: dict[MultiSpaceStopReason, str] = {
    MultiSpaceStopReason.IMPOSSIBLE_REMAINING: (
        "no cabe en ninguno de los tipos de espacio candidatos, en ninguna cantidad"
    ),
    MultiSpaceStopReason.MAX_SPACES_REACHED: (
        "no se procesó: se alcanzó el número máximo de espacios permitido"
    ),
    MultiSpaceStopReason.CANCELLED: "no se procesó: la asignación fue cancelada",
}


class MultiSpaceAssignmentEngine:
    """Punto de entrada único del caso de uso. Sin estado propio salvo el `PackingEngine` usado.

    ``engine = MultiSpaceAssignmentEngine()`` usa un `PackingEngine` por
    defecto (`greedy_extreme_point_v1`); se puede inyectar uno propio
    para pruebas o para una estrategia distinta, igual que
    `PackingEngine` permite sustituir su `PackingStrategy`.
    """

    def __init__(self, packing_engine: PackingEngine | None = None) -> None:
        self._packing_engine = packing_engine or PackingEngine()

    def assign(
        self,
        request: MultiSpaceAssignmentRequest,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[MultiSpaceProgress], None] | None = None,
    ) -> MultiSpaceAssignmentResult:
        """Asigna automáticamente tantos espacios como hagan falta para `request.load_units`."""
        start_time = time.monotonic()
        token = cancellation_token if cancellation_token is not None else CancellationToken()

        total_requested_count = sum(unit.quantity for unit in request.load_units)
        remaining_units = request.load_units
        space_results: list[PackingResult] = []
        warnings: list[str] = []
        stop_reason = MultiSpaceStopReason.ALL_PACKED

        while remaining_units:
            if token.is_cancelled():
                stop_reason = MultiSpaceStopReason.CANCELLED
                break
            if request.max_spaces is not None and len(space_results) >= request.max_spaces:
                stop_reason = MultiSpaceStopReason.MAX_SPACES_REACHED
                break

            space_result = self._select_best_candidate(request, remaining_units, token)
            if space_result is None:
                stop_reason = (
                    MultiSpaceStopReason.CANCELLED
                    if token.is_cancelled()
                    else MultiSpaceStopReason.IMPOSSIBLE_REMAINING
                )
                break

            space_results.append(space_result)
            remaining_units = self._remaining_load_units(remaining_units, space_result)

            total_packed_so_far = sum(result.packed_count for result in space_results)
            self._emit_progress(
                progress_callback,
                warnings,
                len(space_results),
                total_packed_so_far,
                total_requested_count,
                start_time,
            )

            if not remaining_units:
                stop_reason = MultiSpaceStopReason.ALL_PACKED
                break

        final_unpacked_units = (
            ()
            if stop_reason == MultiSpaceStopReason.ALL_PACKED
            else self._units_to_unpacked(remaining_units, stop_reason)
        )
        if final_unpacked_units:
            warnings.append(
                f"La asignación se detuvo por '{stop_reason.value}': "
                f"{len(final_unpacked_units)} instancia(s) sin cargar en ningún espacio."
            )

        return MultiSpaceAssignmentResult(
            space_results=tuple(space_results),
            stop_reason=stop_reason,
            total_requested_count=total_requested_count,
            total_packed_count=sum(result.packed_count for result in space_results),
            final_unpacked_units=final_unpacked_units,
            execution_time_seconds=time.monotonic() - start_time,
            warnings=tuple(warnings),
        )

    def _select_best_candidate(
        self,
        request: MultiSpaceAssignmentRequest,
        remaining_units: tuple[LoadUnit, ...],
        token: CancellationToken,
    ) -> PackingResult | None:
        """Ejecuta el motor sobre TODOS los candidatos de esta ronda y elige el mejor.

        Ningún candidato se descarta de antemano: se optimiza contra
        cada uno de `request.loading_space_candidates` y se compara el
        resultado con una clave de orden estable — nunca se detiene en
        el primero que logra colocar algo. Criterio de comparación,
        exactamente en este orden (ver `docs/MultiSpaceAssignment.md`):

        1. mayor `packed_count` (más unidades cargadas);
        2. mayor `used_volume_cm3`;
        3. mayor `used_weight_kg`;
        4. menor `loading_space.capacity_volume_cm3` (no desperdiciar un
           espacio grande si uno más pequeño logra lo mismo);
        5. orden original de `loading_space_candidates` como desempate
           final — el motor sigue siendo determinista.

        Devuelve `None` cuando ningún candidato coloca ni una sola
        instancia: puede deberse a que la carga restante es realmente
        imposible en cualquiera de los candidatos, o a que la
        ejecución fue cancelada antes de colocar nada — el llamador
        distingue ambos casos consultando `token.is_cancelled()`.
        """
        best_result: PackingResult | None = None
        best_key: tuple[int, float, float, float, int] | None = None

        for candidate_index, candidate in enumerate(request.loading_space_candidates):
            space_request = request.build_space_request(candidate, remaining_units)
            result = self._packing_engine.optimize(space_request, cancellation_token=token)
            if result.packed_count == 0:
                continue

            key = (
                -result.packed_count,
                -result.used_volume_cm3,
                -result.used_weight_kg,
                result.loading_space.capacity_volume_cm3,
                candidate_index,
            )
            if best_key is None or key < best_key:
                best_key = key
                best_result = result

        return best_result

    @staticmethod
    def _remaining_load_units(
        previous_units: tuple[LoadUnit, ...], space_result: PackingResult
    ) -> tuple[LoadUnit, ...]:
        """Recalcula `quantity` por SKU a partir de lo que quedó sin cargar en este espacio.

        Conserva el `id` original de cada `LoadUnit` (`dataclasses.replace`
        solo toca `quantity`), así que el resultado consolidado siempre
        puede reconciliarse contra `request.load_units` por `id`.
        """
        unpacked_counts: dict[UUID, int] = {}
        for unpacked in space_result.unpacked_units:
            unpacked_counts[unpacked.load_unit_id] = (
                unpacked_counts.get(unpacked.load_unit_id, 0) + 1
            )

        remaining: list[LoadUnit] = []
        for unit in previous_units:
            count = unpacked_counts.get(unit.id, 0)
            if count > 0:
                remaining.append(replace(unit, quantity=count))
        return tuple(remaining)

    @staticmethod
    def _units_to_unpacked(
        units: tuple[LoadUnit, ...], stop_reason: MultiSpaceStopReason
    ) -> tuple[UnpackedUnit, ...]:
        reason_text = _STOP_REASON_MESSAGES[stop_reason]
        result: list[UnpackedUnit] = []
        for unit in units:
            for instance_number in range(1, unit.quantity + 1):
                result.append(
                    UnpackedUnit(
                        load_unit_id=unit.id,
                        instance_number=instance_number,
                        reason_code=stop_reason.value,
                        reason_message=f"'{unit.sku}' {reason_text}.",
                    )
                )
        return tuple(result)

    @staticmethod
    def _emit_progress(
        callback: Callable[[MultiSpaceProgress], None] | None,
        warnings: list[str],
        spaces_used: int,
        total_packed_so_far: int,
        total_requested: int,
        start_time: float,
    ) -> None:
        if callback is None:
            return
        progress = MultiSpaceProgress(
            spaces_used=spaces_used,
            current_space_index=spaces_used - 1,
            total_packed_so_far=total_packed_so_far,
            total_requested=total_requested,
            elapsed_seconds=time.monotonic() - start_time,
        )
        try:
            callback(progress)
        except Exception as exc:
            warnings.append(f"El callback de progreso multi-espacio lanzó una excepción: {exc!r}")
