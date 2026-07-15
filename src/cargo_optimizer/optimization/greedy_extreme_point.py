"""GreedyExtremePointStrategy: primer algoritmo real de empaquetado.

Identificador estable: ``greedy_extreme_point_v1``. Diseño completo en
docs/OptimizationEngineDesign.md y docs/GreedyLayerStrategyDesign.md.

No modifica ningún `LoadUnit`, no se salta `RulesEngine`, no usa
aleatoriedad, y nunca lanza una excepción porque una caja no quepa:
esa situación siempre se expresa como `UnpackedUnit`.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.candidate_points import generate_candidate_positions
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.candidates import build_candidate, orientation_fits_loading_space
from cargo_optimizer.optimization.codes import UnpackedReason
from cargo_optimizer.optimization.expander import expand_load_units
from cargo_optimizer.optimization.models import (
    CandidatePlacement,
    PackingProgress,
    PackingRequest,
    PhysicalLoadInstance,
)
from cargo_optimizer.optimization.ordering import order_instances
from cargo_optimizer.optimization.result_builder import ALGORITHM_NAME, build_packing_result
from cargo_optimizer.optimization.state import PackingState
from cargo_optimizer.optimization.strategy import StrategyCapabilities
from cargo_optimizer.rules.codes import LOADING_SPACE_WEIGHT_EXCEEDED
from cargo_optimizer.rules.engine import RulesEngine


class GreedyExtremePointStrategy:
    """Estrategia extreme-point greedy: recorre puntos candidatos con preferencia de menor Z."""

    name = ALGORITHM_NAME

    def capabilities(self) -> StrategyCapabilities:
        return StrategyCapabilities(
            is_deterministic=True,
            supports_cancellation=True,
            supports_time_limit=True,
        )

    def pack(
        self,
        request: PackingRequest,
        rules_engine: RulesEngine,
        cancellation_token: CancellationToken,
        progress_callback: Callable[[PackingProgress], None] | None,
    ) -> PackingResult:
        start_time = time.monotonic()
        deadline = (
            start_time + request.time_limit_seconds
            if request.time_limit_seconds is not None
            else None
        )

        load_units_by_id = {unit.id: unit for unit in request.load_units}
        instances = expand_load_units(request.load_units)
        ordered_instances = order_instances(instances, request.loading_space, rules_engine)
        state = PackingState(load_units_by_id=load_units_by_id)
        orientation_cache: dict[object, tuple[Orientation, ...]] = {}
        total = len(ordered_instances)

        self._emit_progress(progress_callback, state, total, None, start_time)

        stop_reason: UnpackedReason | None = None

        for instance in ordered_instances:
            if cancellation_token.is_cancelled():
                stop_reason = UnpackedReason.CANCELLED
                break
            if deadline is not None and time.monotonic() >= deadline:
                stop_reason = UnpackedReason.TIME_LIMIT_REACHED
                break
            if (
                request.max_iterations is not None
                and state.iteration_count >= request.max_iterations
            ):
                stop_reason = UnpackedReason.ITERATION_LIMIT_REACHED
                break

            self._process_instance(instance, request, rules_engine, state, orientation_cache)
            state.iteration_count += 1
            self._emit_progress(progress_callback, state, total, instance.load_unit.sku, start_time)

        if stop_reason is not None:
            remaining = self._mark_remaining(ordered_instances, state, stop_reason)
            if remaining:
                state.add_warning(
                    f"La ejecución se detuvo por '{stop_reason.value}': "
                    f"{remaining} instancia(s) sin procesar."
                )

        self._emit_progress(progress_callback, state, total, None, start_time)

        return build_packing_result(
            loading_space=request.loading_space,
            placements=state.placements,
            unpacked_units=state.unpacked_units,
            requested_count=total,
            load_units_by_id=load_units_by_id,
            execution_time_seconds=time.monotonic() - start_time,
            warnings=state.warnings,
        )

    def _process_instance(
        self,
        instance: PhysicalLoadInstance,
        request: PackingRequest,
        rules_engine: RulesEngine,
        state: PackingState,
        orientation_cache: dict[object, tuple[Orientation, ...]],
    ) -> None:
        load_unit = instance.load_unit
        if load_unit.id not in orientation_cache:
            orientation_cache[load_unit.id] = rules_engine.allowed_orientations(
                load_unit, request.loading_space
            )
        orientations = orientation_cache[load_unit.id]

        if not orientations:
            state.reject_instance(
                instance,
                UnpackedReason.NO_VALID_ORIENTATION.value,
                f"'{load_unit.sku}' no tiene ninguna orientación permitida.",
            )
            return

        feasible_orientations = [
            (index, orientation)
            for index, orientation in enumerate(orientations)
            if orientation_fits_loading_space(orientation, request.loading_space)
        ]
        if not feasible_orientations:
            state.reject_instance(
                instance,
                UnpackedReason.NO_VALID_ORIENTATION.value,
                f"'{load_unit.sku}' no cabe en '{request.loading_space.name}' en ninguna "
                "orientación permitida, ni siquiera desde el origen.",
            )
            return

        existing_placements = state.placements
        existing_boxes = tuple(box_from_placement(p) for p in existing_placements)
        positions = generate_candidate_positions(existing_placements)

        best: CandidatePlacement | None = None
        violation_codes_seen: set[str] = set()
        generation_index = 0

        for position in positions:
            for orientation_index, orientation in feasible_orientations:
                candidate = build_candidate(
                    instance=instance,
                    position=position,
                    orientation=orientation,
                    orientation_order_index=orientation_index,
                    loading_space=request.loading_space,
                    existing_placements=existing_placements,
                    existing_boxes=existing_boxes,
                    load_units_by_id=state.load_units_by_id,
                    rules_engine=rules_engine,
                    minimum_support_ratio=request.minimum_support_ratio,
                    generation_index=generation_index,
                )
                state.record_candidate_generated()
                generation_index += 1

                if candidate.evaluation.is_allowed:
                    if best is None or candidate.score < best.score:
                        best = candidate
                else:
                    violation_codes_seen.update(v.code for v in candidate.evaluation.violations)

        if best is not None:
            state.accept_placement(best)
            for warning in best.evaluation.warnings:
                state.add_warning(f"'{load_unit.sku}': {warning.message}")
            return

        reason = self._classify_unpacked_reason(violation_codes_seen)
        state.reject_instance(
            instance,
            reason.value,
            f"'{load_unit.sku}' no encontró ninguna posición/orientación válida tras "
            f"{generation_index} candidato(s) evaluado(s).",
        )

    @staticmethod
    def _classify_unpacked_reason(violation_codes: set[str]) -> UnpackedReason:
        if not violation_codes:
            return UnpackedReason.NO_FEASIBLE_POSITION
        if violation_codes == {LOADING_SPACE_WEIGHT_EXCEEDED}:
            return UnpackedReason.LOADING_SPACE_WEIGHT_EXCEEDED
        return UnpackedReason.NO_FEASIBLE_POSITION

    @staticmethod
    def _mark_remaining(
        ordered_instances: tuple[PhysicalLoadInstance, ...],
        state: PackingState,
        reason: UnpackedReason,
    ) -> int:
        packed_keys = {(p.load_unit_id, p.instance_number) for p in state.placements}
        rejected_keys = {(u.load_unit_id, u.instance_number) for u in state.unpacked_units}
        count = 0
        for instance in ordered_instances:
            key = (instance.load_unit.id, instance.instance_number)
            if key in packed_keys or key in rejected_keys:
                continue
            state.reject_instance(
                instance,
                reason.value,
                f"'{instance.load_unit.sku}' no se procesó: ejecución detenida por "
                f"'{reason.value}'.",
            )
            count += 1
        return count

    @staticmethod
    def _emit_progress(
        callback: Callable[[PackingProgress], None] | None,
        state: PackingState,
        total: int,
        current_sku: str | None,
        start_time: float,
    ) -> None:
        if callback is None:
            return
        progress = PackingProgress(
            processed_instances=state.iteration_count,
            total_instances=total,
            packed_count=len(state.placements),
            unpacked_count=len(state.unpacked_units),
            elapsed_seconds=time.monotonic() - start_time,
            current_sku=current_sku,
        )
        try:
            callback(progress)
        except Exception as exc:
            state.add_warning(f"El callback de progreso lanzó una excepción: {exc!r}")
