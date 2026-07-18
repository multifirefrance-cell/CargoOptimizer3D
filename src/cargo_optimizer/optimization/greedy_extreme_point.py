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
from uuid import UUID

from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.candidates import (
    build_candidate,
    orientation_fits_loading_space,
    select_preferred_orientation,
)
from cargo_optimizer.optimization.codes import UnpackedReason
from cargo_optimizer.optimization.expander import expand_load_units
from cargo_optimizer.optimization.models import (
    CandidatePlacement,
    PackingProgress,
    PackingRequest,
    PhysicalLoadInstance,
)
from cargo_optimizer.optimization.ordering import order_instances
from cargo_optimizer.optimization.pattern_packing import PatternCursor, generate_grid_positions
from cargo_optimizer.optimization.result_builder import ALGORITHM_NAME, build_packing_result
from cargo_optimizer.optimization.state import PackingState
from cargo_optimizer.optimization.strategy import StrategyCapabilities
from cargo_optimizer.rules.codes import LOADING_SPACE_WEIGHT_EXCEEDED
from cargo_optimizer.rules.engine import RulesEngine

_PATTERN_MIN_QUANTITY = 8
"""Cantidad mínima de instancias de un mismo `LoadUnit` para intentar el patrón de
filas/capas (fase OPT-17) en vez de resolver cada instancia con una búsqueda completa.

Un número deliberadamente conservador: por debajo de este umbral, la
búsqueda general ya es rápida (pocas instancias) y no vale la pena la
complejidad añadida. No afecta a la corrección en ningún caso — solo a
si se intenta el atajo — porque cada posición generada por el patrón
sigue evaluándose con `RulesEngine.evaluate_placement` completo antes
de aceptarse.
"""


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
        preferred_orientation_cache: dict[UUID, tuple[int, Orientation]] = {}
        pattern_cursors: dict[UUID, PatternCursor] = {}
        total = len(ordered_instances)

        self._emit_progress(progress_callback, state, total, None, start_time)

        stop_reason: UnpackedReason | None = None
        pending_after_round_one: list[PhysicalLoadInstance] = []

        # Ronda 1: cada instancia se coloca usando únicamente la
        # orientación preferida de su Load Unit (ver
        # `select_preferred_orientation`), para que capas sucesivas de la
        # misma unidad mantengan geometría consistente en vez de alternar
        # orientación instancia a instancia. Lo que no encuentra sitio
        # así se pospone a la ronda 2, no se rechaza todavía.
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

            placed = self._try_place_instance(
                instance,
                request,
                rules_engine,
                state,
                orientation_cache,
                preferred_orientation_cache,
                strict=True,
                pattern_cursors=pattern_cursors,
            )
            if not placed:
                pending_after_round_one.append(instance)
            state.iteration_count += 1
            self._emit_progress(progress_callback, state, total, instance.load_unit.sku, start_time)

        # Ronda 2: solo para lo que la ronda 1 no pudo colocar. Se
        # reintenta con todas las orientaciones factibles (no solo la
        # preferida), aprovechando huecos residuales que ninguna
        # instancia de esta Load Unit pudo llenar manteniendo su
        # orientación consistente — sin esta ronda, algunas unidades que
        # sí caben (rotadas, en el remanente junto a una pared) quedarían
        # sin cargar de forma innecesaria. Nunca se ejecuta si la ronda 1
        # ya se detuvo por cancelación/límite de tiempo/iteraciones: esas
        # instancias pendientes se marcan igual que antes en
        # `_mark_remaining`.
        if stop_reason is None:
            for instance in pending_after_round_one:
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

                self._try_place_instance(
                    instance,
                    request,
                    rules_engine,
                    state,
                    orientation_cache,
                    preferred_orientation_cache,
                    strict=False,
                )
                state.iteration_count += 1
                self._emit_progress(
                    progress_callback, state, total, instance.load_unit.sku, start_time
                )

        if stop_reason is not None:
            remaining = self._mark_remaining(ordered_instances, state, stop_reason)
            if remaining:
                state.add_warning(
                    f"La ejecución se detuvo por '{stop_reason.value}': "
                    f"{remaining} instancia(s) sin procesar."
                )

        self._emit_progress(progress_callback, state, total, None, start_time)

        warnings = state.warnings
        if request.diagnostic_mode:
            warnings = (
                *warnings,
                f"[diagnostic] candidates_generated={state.candidate_generation_count}",
            )

        return build_packing_result(
            loading_space=request.loading_space,
            placements=state.placements,
            unpacked_units=state.unpacked_units,
            requested_count=total,
            load_units_by_id=load_units_by_id,
            execution_time_seconds=time.monotonic() - start_time,
            warnings=warnings,
        )

    def _try_place_instance(
        self,
        instance: PhysicalLoadInstance,
        request: PackingRequest,
        rules_engine: RulesEngine,
        state: PackingState,
        orientation_cache: dict[object, tuple[Orientation, ...]],
        preferred_orientation_cache: dict[UUID, tuple[int, Orientation]],
        strict: bool,
        pattern_cursors: dict[UUID, PatternCursor] | None = None,
    ) -> bool:
        """Intenta colocar `instance`; devuelve `True` si se aceptó un placement.

        `strict=True` (ronda 1 de `pack`): solo se prueba la orientación
        preferida del Load Unit (`select_preferred_orientation`) — la que
        mejor tesela el piso, fijada una única vez por unidad para que
        instancias sucesivas de la misma unidad mantengan geometría
        consistente en vez de alternar orientación instancia a instancia
        (la causa raíz de los "muros"/columnas aisladas documentada en
        `docs/OptimizationEngine.md`). Si no hay ninguna colocación
        válida así, se devuelve `False` **sin** rechazar la instancia:
        `pack` la reintenta en la ronda 2.

        `strict=False` (ronda 2, o la única ronda cuando el Load Unit no
        tiene ninguna orientación factible): se prueban todas las
        orientaciones factibles a la vez, como red de seguridad para no
        dejar sin cargar una unidad que sí cabría rotada (p. ej. en un
        hueco residual junto a una pared que la orientación preferida no
        puede llenar). Si tampoco así hay colocación válida, la instancia
        se rechaza aquí de forma definitiva (`state.reject_instance`).

        `pattern_cursors` (fase OPT-17, solo se usa cuando `strict=True`
        y hay suficiente cantidad — ver `_PATTERN_MIN_QUANTITY` y
        `optimization/pattern_packing.py`): si ya existe un patrón de
        filas/capas en curso para este `LoadUnit`, se prueba directamente
        su siguiente posición (un único candidato, evaluado con
        `RulesEngine` completo, igual que cualquier otro) en vez de
        recorrer todos los puntos candidatos disponibles. Si esa posición
        falla, el patrón se marca agotado y esta instancia (solo esta)
        cae a la búsqueda general de más abajo, sin perder ninguna
        colocación posible.
        """
        load_unit = instance.load_unit

        if strict and pattern_cursors is not None:
            cursor = pattern_cursors.get(load_unit.id)
            if cursor is not None and not cursor.exhausted:
                placed = self._try_pattern_position(instance, request, rules_engine, state, cursor)
                if placed:
                    return True
                cursor.exhausted = True
                # No se pierde esta instancia: cae a la búsqueda general
                # de más abajo, exactamente como si nunca hubiera existido
                # un patrón para este LoadUnit.
        if load_unit.id not in orientation_cache:
            orientation_cache[load_unit.id] = rules_engine.allowed_orientations(
                load_unit, request.loading_space
            )
        orientations = orientation_cache[load_unit.id]

        if not orientations:
            if strict:
                return False
            state.reject_instance(
                instance,
                UnpackedReason.NO_VALID_ORIENTATION.value,
                f"'{load_unit.sku}' no tiene ninguna orientación permitida.",
            )
            return False

        feasible_orientations = [
            (index, orientation)
            for index, orientation in enumerate(orientations)
            if orientation_fits_loading_space(orientation, request.loading_space)
        ]
        if not feasible_orientations:
            if strict:
                return False
            state.reject_instance(
                instance,
                UnpackedReason.NO_VALID_ORIENTATION.value,
                f"'{load_unit.sku}' no cabe en '{request.loading_space.name}' en ninguna "
                "orientación permitida, ni siquiera desde el origen.",
            )
            return False

        if load_unit.id not in preferred_orientation_cache:
            preferred_orientation_cache[load_unit.id] = select_preferred_orientation(
                feasible_orientations, request.loading_space
            )
        preferred_index, preferred_orientation = preferred_orientation_cache[load_unit.id]

        existing_placements = state.placements
        existing_boxes = state.accepted_boxes
        existing_bounding_dimensions = state.bounding_dimensions
        positions, pruned_violation_codes = state.cached_pruned_candidate_positions(
            request.loading_space
        )

        violation_codes_seen: set[str] = set(pruned_violation_codes)
        orientation_options = (
            ((preferred_index, preferred_orientation),) if strict else tuple(feasible_orientations)
        )

        best, generation_index = self._search_best_candidate(
            instance=instance,
            request=request,
            rules_engine=rules_engine,
            state=state,
            positions=positions,
            orientation_options=orientation_options,
            existing_placements=existing_placements,
            existing_boxes=existing_boxes,
            existing_bounding_dimensions=existing_bounding_dimensions,
            violation_codes_seen=violation_codes_seen,
            generation_index=0,
        )

        if best is not None:
            state.accept_placement(best)
            for warning in best.evaluation.warnings:
                state.add_warning(f"'{load_unit.sku}': {warning.message}")
            if (
                strict
                and pattern_cursors is not None
                and load_unit.id not in pattern_cursors
                and load_unit.quantity >= _PATTERN_MIN_QUANTITY
            ):
                pattern_cursors[load_unit.id] = self._start_pattern_cursor(
                    request, preferred_index, preferred_orientation, best.position
                )
            return True

        if strict:
            return False

        reason = self._classify_unpacked_reason(violation_codes_seen)
        state.reject_instance(
            instance,
            reason.value,
            f"'{load_unit.sku}' no encontró ninguna posición/orientación válida tras "
            f"{generation_index} candidato(s) evaluado(s).",
        )
        return False

    @staticmethod
    def _start_pattern_cursor(
        request: PackingRequest,
        orientation_index: int,
        orientation: Orientation,
        anchor: Position3D,
    ) -> PatternCursor:
        """Inicia un patrón de filas/capas a partir de la primera colocación real
        (`anchor`) de un `LoadUnit` con cantidad grande — fase OPT-17.

        `anchor` viene de una búsqueda completa real (`_search_best_candidate`),
        así que ya respeta cualquier otra caja u otro SKU colocado antes; el
        patrón solo avanza geométricamente desde ahí (fila, luego capa),
        dejando que `RulesEngine` valide cada posición generada.
        """
        dims = request.loading_space.internal_dimensions
        positions = generate_grid_positions(
            anchor=anchor,
            x_size_cm=orientation.x_size_cm,
            y_size_cm=orientation.y_size_cm,
            z_size_cm=orientation.z_size_cm,
            length_cm=dims.length_cm,
            width_cm=dims.width_cm,
            height_cm=dims.height_cm,
        )
        next(positions, None)  # `anchor` ya está colocado: se descarta.
        return PatternCursor(
            orientation=orientation, orientation_index=orientation_index, positions=positions
        )

    @staticmethod
    def _try_pattern_position(
        instance: PhysicalLoadInstance,
        request: PackingRequest,
        rules_engine: RulesEngine,
        state: PackingState,
        cursor: PatternCursor,
    ) -> bool:
        """Prueba la siguiente posición del patrón de `cursor` para `instance`.

        Un único candidato, evaluado con `RulesEngine.evaluate_placement`
        completo (colisión, soporte, apilamiento, peso, fragilidad,
        orientación, extintor) — nunca se salta ninguna regla. `devuelve
        True` si se aceptó; `False` si la posición no era válida (o si el
        patrón ya no tiene más posiciones dentro de límites), sin haber
        rechazado `instance` — quien llama decide qué hacer a continuación.
        """
        position = cursor.next_position()
        if position is None:
            return False

        candidate = build_candidate(
            instance=instance,
            position=position,
            orientation=cursor.orientation,
            orientation_order_index=cursor.orientation_index,
            loading_space=request.loading_space,
            existing_placements=state.placements,
            existing_boxes=state.accepted_boxes,
            existing_bounding_dimensions=state.bounding_dimensions,
            load_units_by_id=state.load_units_by_id,
            rules_engine=rules_engine,
            minimum_support_ratio=request.minimum_support_ratio,
            generation_index=0,
            spatial_index=state.spatial_index,
            box_by_sequence_number=state.box_by_sequence_number,
            stack_level_by_sequence_number=state.stack_level_by_sequence_number,
            placement_by_sequence_number=state.placement_by_sequence_number,
            total_weight_kg=state.packed_weight_kg,
        )
        state.record_candidate_generated()
        if not candidate.evaluation.is_allowed:
            return False

        state.accept_placement(candidate)
        for warning in candidate.evaluation.warnings:
            state.add_warning(f"'{instance.load_unit.sku}': {warning.message}")
        return True

    @staticmethod
    def _search_best_candidate(
        instance: PhysicalLoadInstance,
        request: PackingRequest,
        rules_engine: RulesEngine,
        state: PackingState,
        positions: tuple[Position3D, ...],
        orientation_options: tuple[tuple[int, Orientation], ...],
        existing_placements: tuple[Placement, ...],
        existing_boxes: tuple[AxisAlignedBox, ...],
        existing_bounding_dimensions: tuple[float, float, float],
        violation_codes_seen: set[str],
        generation_index: int,
    ) -> tuple[CandidatePlacement | None, int]:
        """Recorre `positions` x `orientation_options` y devuelve el mejor candidato válido.

        Extraído de `_process_instance` para poder invocarse dos veces
        (orientación preferida primero, luego el resto como red de
        seguridad) sin duplicar el bucle. `violation_codes_seen` se
        actualiza in-place; el índice de generación devuelto continúa
        desde donde lo dejó la llamada anterior, para que
        `generation_index` (desempate final del score) siga siendo
        consistente entre ambas pasadas.

        Corte temprano por posición (fase OPT-16, ver
        `docs/OptimizerPerformance.md`): `positions` ya llega ordenado
        ascendentemente por `(z, x, y)` (`geometry.candidate_points.
        generate_candidate_positions`), y `score_candidate` compara
        exactamente `(z, x, y, ...)` en ese mismo orden como los tres
        primeros componentes del score (ver `optimization/scoring.py`).
        Como las posiciones, ya sin duplicados, son estrictamente
        crecientes en ese orden, ningún candidato en una posición
        posterior puede tener un score menor que el mejor candidato ya
        encontrado en una posición anterior — se compara primero
        `(z, x, y)`, y toda posición posterior tiene ese prefijo
        estrictamente mayor. Por eso, en cuanto **alguna** orientación
        resulta válida en una posición (probadas todas las de
        `orientation_options` para esa posición, que sí pueden
        desempatar entre sí por soporte/volumen/residual/orientación),
        se puede dejar de recorrer posiciones posteriores: no es una
        heurística de "punto dominado" (la que el diseño original de
        `pruning.py` descarta explícitamente) sino una consecuencia
        matemática exacta y determinista del propio orden lexicográfico
        del score, nunca una aproximación — mismo resultado exacto que
        recorrer todas las posiciones y quedarse con el score mínimo,
        confirmado por `tests/optimization/test_regression_greedy_extreme_point.py`
        (conteos de referencia sin cambios). Cuando ninguna posición
        resulta válida, se recorren todas igual que antes, así que
        `violation_codes_seen` sigue recogiendo exactamente los mismos
        códigos que antes de esta fase.
        """
        best: CandidatePlacement | None = None
        for position in positions:
            position_best: CandidatePlacement | None = None
            for orientation_index, orientation in orientation_options:
                candidate = build_candidate(
                    instance=instance,
                    position=position,
                    orientation=orientation,
                    orientation_order_index=orientation_index,
                    loading_space=request.loading_space,
                    existing_placements=existing_placements,
                    existing_boxes=existing_boxes,
                    existing_bounding_dimensions=existing_bounding_dimensions,
                    load_units_by_id=state.load_units_by_id,
                    rules_engine=rules_engine,
                    minimum_support_ratio=request.minimum_support_ratio,
                    generation_index=generation_index,
                    spatial_index=state.spatial_index,
                    box_by_sequence_number=state.box_by_sequence_number,
                    stack_level_by_sequence_number=state.stack_level_by_sequence_number,
                    placement_by_sequence_number=state.placement_by_sequence_number,
                    total_weight_kg=state.packed_weight_kg,
                )
                state.record_candidate_generated()
                generation_index += 1

                if candidate.evaluation.is_allowed:
                    if position_best is None or candidate.score < position_best.score:
                        position_best = candidate
                else:
                    violation_codes_seen.update(v.code for v in candidate.evaluation.violations)

            if position_best is not None:
                best = position_best
                break

        return best, generation_index

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
