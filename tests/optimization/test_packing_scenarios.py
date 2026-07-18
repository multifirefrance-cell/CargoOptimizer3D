"""Escenarios de packing de extremo a extremo sobre PackingEngine.

No se afirma optimalidad matemática en ningún momento: solo
corrección, determinismo y cumplimiento de las reglas ya validadas en
`tests/rules` y `tests/geometry`.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.collision import find_overlapping_placements
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.codes import UnpackedReason
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingProgress, PackingRequest
from tests.optimization._helpers import DEFAULT_SPACE, make_individual_extinguisher, make_load_unit

_DIMS = Dimensions3D(40.0, 30.0, 20.0)
# Caja cúbica: la misma huella de piso (30x30) en cualquiera de las 6
# orientaciones, así un "tight_space" de 30x30xN fuerza capacidad 1 por
# piso sin importar qué orientación elija el motor — a diferencia de
# `_DIMS` (40x30x20), donde una orientación rotada (20x30 de huella)
# puede duplicar la capacidad de piso y abrir espacio junto a la
# primera caja. Se usa en las pruebas de apilamiento/fragilidad de más
# abajo, que necesitan aislar "no cabe nada más al lado" de verdad.
_CUBE_DIMS = Dimensions3D(30.0, 30.0, 30.0)


def _space(length: float, width: float, height: float, **overrides: object) -> LoadingSpace:
    kwargs: dict[str, object] = {
        "name": "Espacio de prueba",
        "category": LoadingSpaceCategory.TRUCK,
        "internal_dimensions": Dimensions3D(length, width, height),
    }
    kwargs.update(overrides)
    return LoadingSpace(**kwargs)  # type: ignore[arg-type]


# --- 1-3: casos básicos -----------------------------------------------------------


def test_empty_request_is_valid_with_zero_placements() -> None:
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=())
    result = PackingEngine().optimize(request)
    assert result.packed_count == 0
    assert result.requested_count == 0
    assert result.placements == ()


def test_single_box_that_fits() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=1)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    placement = result.placements[0]
    assert (placement.x_cm, placement.y_cm, placement.z_cm) == (0.0, 0.0, 0.0)


def test_box_that_does_not_fit() -> None:
    huge = make_load_unit(dimensions=Dimensions3D(500.0, 500.0, 500.0), quantity=1)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(huge,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 0
    assert len(result.unpacked_units) == 1
    assert result.unpacked_units[0].reason_code == UnpackedReason.NO_VALID_ORIENTATION.value


# --- 4-6: alineación y apilamiento -------------------------------------------------


def test_two_boxes_aligned_in_y_by_default() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=2)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 2
    positions = sorted((p.x_cm, p.y_cm, p.z_cm) for p in result.placements)
    assert positions == [(0.0, 0.0, 0.0), (0.0, 30.0, 0.0)]


def test_two_boxes_aligned_in_x_when_y_has_no_room() -> None:
    narrow_space = _space(200.0, 30.0, 100.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=2)
    request = PackingRequest(loading_space=narrow_space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 2
    positions = sorted((p.x_cm, p.y_cm, p.z_cm) for p in result.placements)
    # La orientación preferida ya no es necesariamente LWH_XYZ (huella
    # 40x30): `select_preferred_orientation` fija, una vez por Load
    # Unit, la orientación que maximiza cuántas unidades caben por piso
    # (ver docs/OptimizationEngine.md) — en este espacio de 30 cm de
    # ancho, HWL_XYZ (huella 20x30) tesela el doble de veces en los 200
    # cm de largo (10 huecos de 20 cm frente a 5 de 40 cm), así que las
    # dos cajas quedan alineadas en X cada 20 cm, no 40.
    assert positions == [(0.0, 0.0, 0.0), (20.0, 0.0, 0.0)]


def test_two_boxes_stacked_in_z_when_no_room_beside() -> None:
    # Caja cúbica (ver `_CUBE_DIMS`): con `_DIMS` (40x30x20), una
    # orientación rotada (huella 20x30) cabría dos veces en un
    # tight_space de 40 cm de largo, contradiciendo el propio nombre de
    # esta prueba ("no room beside") — la huella cúbica no cambia con la
    # orientación, así que "no hay sitio al lado" sigue siendo cierto
    # sea cual sea la orientación elegida.
    tight_space = _space(30.0, 30.0, 100.0)
    unit = make_load_unit(dimensions=_CUBE_DIMS, quantity=2, max_stack_count=2)
    request = PackingRequest(loading_space=tight_space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 2
    positions = sorted((p.x_cm, p.y_cm, p.z_cm) for p in result.placements)
    assert positions == [(0.0, 0.0, 0.0), (0.0, 0.0, 30.0)]


def test_contact_between_boxes_is_not_treated_as_collision() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=2)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert find_overlapping_placements(result.placements) == ()


# --- 9-11: peso, apilamiento, fragilidad -------------------------------------------


def test_loading_space_weight_limit_is_respected() -> None:
    # Una única instancia, sin nada colocado todavía: así el candidato en el origen
    # nunca colisiona con nada y el suelo siempre da soporte completo en cualquier
    # orientación, aislando el peso como única restricción posible. Con más de una
    # instancia ya colocada, el candidato en el origen colisionaría con lo existente
    # y algunas orientaciones tendrían soporte parcial, añadiendo otros códigos al
    # conjunto y hasta obtenerse el motivo general NO_FEASIBLE_POSITION en su lugar
    # (comportamiento correcto, no un bug: solo hay que aislar la variable en el test).
    space = _space(200.0, 100.0, 100.0, max_weight_kg=15.0)
    unit = make_load_unit(dimensions=_DIMS, weight_kg=20.0, quantity=1)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 0
    assert len(result.unpacked_units) == 1
    expected_reason = UnpackedReason.LOADING_SPACE_WEIGHT_EXCEEDED.value
    assert result.unpacked_units[0].reason_code == expected_reason


def test_loading_space_weight_limit_partial_pack() -> None:
    space = _space(200.0, 100.0, 100.0, max_weight_kg=15.0)
    unit = make_load_unit(dimensions=_DIMS, weight_kg=10.0, quantity=3, max_stack_count=5)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    assert len(result.unpacked_units) == 2
    assert result.used_weight_kg == 10.0


def test_max_stack_count_is_respected() -> None:
    # Caja cúbica (ver `_CUBE_DIMS`, mismo motivo que
    # `test_two_boxes_stacked_in_z_when_no_room_beside`): con `_DIMS`
    # una orientación rotada abriría sitio junto a la primera caja y
    # esta prueba dejaría de aislar la regla de apilamiento.
    tight_space = _space(30.0, 30.0, 100.0)
    unit = make_load_unit(dimensions=_CUBE_DIMS, quantity=2, max_stack_count=1)
    request = PackingRequest(loading_space=tight_space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    assert len(result.unpacked_units) == 1


def test_fragility_prevents_stacking_on_top() -> None:
    tight_space = _space(30.0, 30.0, 100.0)
    fragile_unit = make_load_unit(
        sku="FRAGILE",
        dimensions=_CUBE_DIMS,
        weight_kg=50.0,
        fragile=True,
        max_stack_count=2,
        quantity=1,
    )
    normal_unit = make_load_unit(
        sku="NORMAL", dimensions=_CUBE_DIMS, weight_kg=5.0, max_stack_count=2, quantity=1
    )
    request = PackingRequest(loading_space=tight_space, load_units=(fragile_unit, normal_unit))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    assert len(result.unpacked_units) == 1
    assert result.placements[0].load_unit_id == fragile_unit.id


# --- 12: extintor individual --------------------------------------------------------


def test_individual_extinguisher_stays_horizontal_axis_x_and_unstacked() -> None:
    tight_space = _space(60.0, 20.0, 100.0)
    extinguisher = make_individual_extinguisher(nominal_kg=5.0, quantity=2, max_stack_count=5)
    request = PackingRequest(loading_space=tight_space, load_units=(extinguisher,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    assert len(result.unpacked_units) == 1
    placement = result.placements[0]
    assert placement.orientation.code in (OrientationCode.LWH_XYZ, OrientationCode.LHW_XYZ)
    assert placement.z_cm == 0.0


# --- 16-18: quantity, determinismo, SKU mezclados ----------------------------------


def test_quantity_generates_correct_instance_numbers() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=4)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 4
    instance_numbers = {p.instance_number for p in result.placements}
    assert instance_numbers == {1, 2, 3, 4}


def test_determinism_across_repeated_runs() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=6)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    engine = PackingEngine()
    result_a = engine.optimize(request)
    result_b = engine.optimize(request)
    assert result_a.placements == result_b.placements
    assert result_a.unpacked_units == result_b.unpacked_units
    assert result_a.warnings == result_b.warnings
    assert result_a.packed_count == result_b.packed_count


def test_mixed_skus_are_packed_correctly() -> None:
    unit_a = make_load_unit(sku="A", dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=2)
    unit_b = make_load_unit(sku="B", dimensions=Dimensions3D(20.0, 20.0, 20.0), quantity=2)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit_a, unit_b))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 4
    assert find_overlapping_placements(result.placements) == ()


# --- 19-23: resultados parciales, límites, cancelación -----------------------------


def test_partial_result_when_not_everything_fits() -> None:
    tight_space = _space(40.0, 30.0, 20.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=5)
    request = PackingRequest(loading_space=tight_space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.packed_count == 1
    assert len(result.unpacked_units) == 4
    assert result.packed_count + len(result.unpacked_units) == result.requested_count


def test_time_limit_produces_partial_result_without_losing_instances() -> None:
    unit = make_load_unit(dimensions=Dimensions3D(5.0, 5.0, 5.0), quantity=200)
    huge_space = _space(1000.0, 1000.0, 1000.0)
    request = PackingRequest(loading_space=huge_space, load_units=(unit,), time_limit_seconds=1e-9)
    result = PackingEngine().optimize(request)
    assert result.packed_count + len(result.unpacked_units) == result.requested_count
    if result.unpacked_units:
        assert all(
            u.reason_code == UnpackedReason.TIME_LIMIT_REACHED.value for u in result.unpacked_units
        )
        assert any("time_limit_reached" in w for w in result.warnings)


def test_max_iterations_stops_after_exact_count() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=5)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,), max_iterations=2)
    result = PackingEngine().optimize(request)
    assert result.packed_count == 2
    assert len(result.unpacked_units) == 3
    assert all(
        u.reason_code == UnpackedReason.ITERATION_LIMIT_REACHED.value for u in result.unpacked_units
    )


def test_cancellation_before_start() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=3)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    token = CancellationToken()
    token.cancel()
    result = PackingEngine().optimize(request, cancellation_token=token)
    assert result.packed_count == 0
    assert len(result.unpacked_units) == 3
    assert all(u.reason_code == UnpackedReason.CANCELLED.value for u in result.unpacked_units)


def test_cancellation_during_execution() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=5)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    token = CancellationToken()

    def cancel_after_two(progress: PackingProgress) -> None:
        if progress.processed_instances >= 2:
            token.cancel()

    result = PackingEngine().optimize(
        request, cancellation_token=token, progress_callback=cancel_after_two
    )
    assert result.packed_count + len(result.unpacked_units) == 5
    assert result.packed_count < 5
    assert any(u.reason_code == UnpackedReason.CANCELLED.value for u in result.unpacked_units)


# --- 25-29: validación final, límites, volumen y peso ------------------------------


def test_no_overlap_in_final_layout() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=8)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert find_overlapping_placements(result.placements) == ()


def test_all_placements_within_bounds() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=8)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    for placement in result.placements:
        box = box_from_placement(placement)
        assert fits_inside_loading_space(box, DEFAULT_SPACE)


def test_used_volume_is_correct() -> None:
    unit = make_load_unit(dimensions=_DIMS, quantity=3)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    expected = result.packed_count * _DIMS.volume_cm3
    assert result.used_volume_cm3 == expected


def test_used_weight_is_correct() -> None:
    unit = make_load_unit(dimensions=_DIMS, weight_kg=12.5, quantity=3)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    expected = result.packed_count * 12.5
    assert result.used_weight_kg == expected


# --- 30: grouped_box no confunde requested_count con total_requested_units --------


def test_grouped_box_requested_count_counts_boxes_not_internal_units() -> None:
    from tests.optimization._helpers import make_grouped_extinguisher

    unit = make_grouped_extinguisher(nominal_kg=1.0, units_per_package=10, quantity=3)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)
    assert result.requested_count == 3
    assert result.packed_count == 3
