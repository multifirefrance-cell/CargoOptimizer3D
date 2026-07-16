"""Pruebas de `MultiSpaceAssignmentEngine`: asignación automática multi-espacio."""

from __future__ import annotations

from dataclasses import replace

import pytest

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.models import MultiSpaceAssignmentRequest, MultiSpaceProgress
from cargo_optimizer.application.multi_space_assignment import MultiSpaceAssignmentEngine
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.cancellation import CancellationToken
from tests.application._helpers import LARGE_SPACE, SMALL_SPACE, make_load_unit


def _cube_60(quantity: int) -> tuple:
    # Un cubo de 60 cm no puede compartir espacio con otro dentro de un
    # `SMALL_SPACE` de 100x100x100: en cualquier eje, dos instancias
    # necesitarían 120 cm, más que los 100 disponibles. Garantiza,
    # geométricamente, exactamente una instancia por espacio.
    return (
        make_load_unit(
            sku="CUBE",
            dimensions=Dimensions3D(60.0, 60.0, 60.0),
            weight_kg=5.0,
            quantity=quantity,
        ),
    )


def test_single_space_suffices() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(make_load_unit(quantity=5),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert result.is_fully_packed
    assert result.spaces_used_count == 1
    assert result.total_packed_count == 5
    assert result.total_requested_count == 5
    assert result.final_unpacked_units == ()


def test_needs_multiple_spaces() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert result.is_fully_packed
    assert result.spaces_used_count == 3
    assert result.total_packed_count == 3
    assert all(space_result.packed_count == 1 for space_result in result.space_results)


def test_impossible_load_reports_final_unpacked_units() -> None:
    oversized = make_load_unit(
        sku="TOO-BIG",
        dimensions=Dimensions3D(500.0, 500.0, 500.0),
        weight_kg=10.0,
        quantity=1,
    )
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE, LARGE_SPACE),
        load_units=(oversized,),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.stop_reason == MultiSpaceStopReason.IMPOSSIBLE_REMAINING
    assert not result.is_fully_packed
    assert result.spaces_used_count == 0
    assert result.total_packed_count == 0
    assert len(result.final_unpacked_units) == 1
    assert result.final_unpacked_units[0].load_unit_id == oversized.id
    assert result.warnings


def test_max_spaces_cap_stops_early() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
        max_spaces=2,
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.stop_reason == MultiSpaceStopReason.MAX_SPACES_REACHED
    assert result.spaces_used_count == 2
    assert result.total_packed_count == 2
    assert len(result.final_unpacked_units) == 1


def test_cancellation_stops_before_next_space() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
    )
    token = CancellationToken()
    progress_events: list[MultiSpaceProgress] = []

    def on_progress(progress: MultiSpaceProgress) -> None:
        progress_events.append(progress)
        if progress.spaces_used >= 1:
            token.cancel()

    result = MultiSpaceAssignmentEngine().assign(
        request, cancellation_token=token, progress_callback=on_progress
    )

    assert result.stop_reason == MultiSpaceStopReason.CANCELLED
    assert result.spaces_used_count == 1
    assert len(result.final_unpacked_units) == 2


def test_falls_back_to_second_candidate_when_first_cannot_fit_anything() -> None:
    unit = make_load_unit(
        sku="MEDIUM",
        dimensions=Dimensions3D(250.0, 150.0, 150.0),
        weight_kg=20.0,
        quantity=1,
    )
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE, LARGE_SPACE),
        load_units=(unit,),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert result.spaces_used_count == 1
    assert result.space_results[0].loading_space is LARGE_SPACE


def test_deterministic_across_runs() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE, LARGE_SPACE),
        load_units=(
            make_load_unit(sku="A", quantity=4),
            *_cube_60(quantity=2),
        ),
    )
    engine = MultiSpaceAssignmentEngine()
    first = engine.assign(request)
    second = engine.assign(request)

    assert first.stop_reason == second.stop_reason
    assert first.spaces_used_count == second.spaces_used_count
    assert first.total_packed_count == second.total_packed_count
    assert [r.packed_count for r in first.space_results] == [
        r.packed_count for r in second.space_results
    ]


def test_progress_callback_invoked_once_per_space() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
    )
    events: list[MultiSpaceProgress] = []
    MultiSpaceAssignmentEngine().assign(request, progress_callback=events.append)

    assert [event.spaces_used for event in events] == [1, 2, 3]
    assert [event.total_packed_so_far for event in events] == [1, 2, 3]
    assert all(event.total_requested == 3 for event in events)


def test_progress_callback_exception_becomes_warning_not_propagated() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=1),
    )

    def broken_callback(_: MultiSpaceProgress) -> None:
        raise RuntimeError("boom")

    result = MultiSpaceAssignmentEngine().assign(request, progress_callback=broken_callback)

    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert any("boom" in warning for warning in result.warnings)


def test_empty_load_units_is_trivially_fully_packed() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.is_fully_packed
    assert result.spaces_used_count == 0
    assert result.total_requested_count == 0
    assert result.total_packed_count == 0


def test_aggregate_volume_properties() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(make_load_unit(quantity=1),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.spaces_used_count == 1
    expected_capacity = SMALL_SPACE.capacity_volume_cm3
    assert result.total_capacity_volume_cm3 == expected_capacity
    assert result.total_used_volume_cm3 > 0
    assert 0 < result.overall_volume_utilization_percent < 100


def test_selects_higher_packed_count_even_when_first_candidate_already_fits_something() -> None:
    # SMALL_SPACE (100x100x100) también puede cargar algo de este pedido
    # (no coloca cero, así que la estrategia antigua "el primero que
    # funcione" se habría quedado con él) — pero LARGE_SPACE
    # (300x200x200) coloca más unidades del mismo pedido en una sola
    # ronda. El motor debe evaluar ambos y quedarse con el que carga
    # más, no con el primero que consigue algo.
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE, LARGE_SPACE),
        load_units=(make_load_unit(quantity=50),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.space_results[0].loading_space is LARGE_SPACE

    # Control: con SMALL_SPACE como único candidato, el mismo pedido
    # necesita más espacios en total — confirma que elegir LARGE_SPACE
    # de entrada produce un mejor resultado global, no solo un empate.
    small_only_request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(make_load_unit(quantity=50),),
    )
    small_only_result = MultiSpaceAssignmentEngine().assign(small_only_request)

    assert small_only_result.spaces_used_count > result.spaces_used_count


def test_tie_break_prefers_smaller_capacity_when_packed_count_and_volume_tie() -> None:
    big_capacity_candidate = LoadingSpace(
        name="Candidato con mucha capacidad de sobra",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    )
    small_capacity_candidate = LoadingSpace(
        name="Candidato con la capacidad justa",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(70.0, 70.0, 70.0),
    )
    # Una sola caja cabe igual de bien en ambos: mismo packed_count,
    # mismo used_volume_cm3, mismo used_weight_kg. Solo difiere la
    # capacidad del espacio — debe ganar el más pequeño, sin desperdiciar
    # espacio de sobra.
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(big_capacity_candidate, small_capacity_candidate),
        load_units=(make_load_unit(quantity=1),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.space_results[0].loading_space is small_capacity_candidate


def test_tie_break_falls_back_to_original_order_when_everything_else_ties() -> None:
    first_candidate = LoadingSpace(
        name="Empate — primero en la lista",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    )
    second_candidate = replace(first_candidate, name="Empate — segundo en la lista")
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(first_candidate, second_candidate),
        load_units=(make_load_unit(quantity=1),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.space_results[0].loading_space is first_candidate


def test_spaces_used_by_candidate_name() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert dict(result.spaces_used_by_candidate_name) == {SMALL_SPACE.name: 3}


def test_overall_weight_utilization_percent_none_without_declared_limit() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(make_load_unit(quantity=1, weight_kg=10.0),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.overall_weight_utilization_percent is None


def test_overall_weight_utilization_percent_computed_when_limit_declared() -> None:
    space_with_limit = replace(SMALL_SPACE, max_weight_kg=100.0)
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(space_with_limit,),
        load_units=(make_load_unit(quantity=1, weight_kg=10.0),),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.overall_weight_utilization_percent == 10.0


def test_average_max_min_volume_utilization_percent() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.min_volume_utilization_percent <= result.average_volume_utilization_percent + 1e-9
    assert result.average_volume_utilization_percent <= result.max_volume_utilization_percent + 1e-9
    assert result.max_volume_utilization_percent > 0
    # Los tres espacios usados son idénticos (mismo SMALL_SPACE, mismo
    # cubo): la ocupación de cada ronda es esencialmente la misma
    # (una diferencia de punto flotante en la media es aceptable).
    assert result.min_volume_utilization_percent == pytest.approx(
        result.max_volume_utilization_percent
    )


def test_pending_count_matches_final_unpacked_units() -> None:
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=_cube_60(quantity=3),
        max_spaces=2,
    )
    result = MultiSpaceAssignmentEngine().assign(request)

    assert result.pending_count == len(result.final_unpacked_units) == 1


def test_uses_injected_packing_engine() -> None:
    from cargo_optimizer.optimization.engine import PackingEngine

    engine = MultiSpaceAssignmentEngine(packing_engine=PackingEngine())
    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(SMALL_SPACE,),
        load_units=(make_load_unit(quantity=1),),
    )
    result = engine.assign(request)

    assert result.is_fully_packed
