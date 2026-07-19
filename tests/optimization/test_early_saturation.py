"""Saturación temprana del espacio de carga (fase OPT-18).

Verifica que `GreedyExtremePointStrategy` deja de repetir búsquedas
idénticas para instancias de un `LoadUnit` ya confirmado sin ninguna
posición factible en el `PackingState` actual -- sin perder ninguna
caja que sí cabría, sin afectar a otros SKU, y sin romper ninguna
regla de negocio (apilamiento, orientación, extintores, colisión,
límites, soporte).
"""

from __future__ import annotations

import re

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.collision import find_overlapping_placements
from cargo_optimizer.geometry.support import is_supported
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from tests.optimization._helpers import make_individual_extinguisher, make_load_unit

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _space(length: float, width: float, height: float) -> LoadingSpace:
    return LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(length, width, height),
    )


def _candidates_generated(warnings: tuple[str, ...]) -> int:
    for warning in warnings:
        match = re.search(r"candidates_generated=(\d+)", warning)
        if match:
            return int(match.group(1))
    raise AssertionError(f"No se encontró el aviso de diagnóstico en {warnings!r}")


def test_all_instances_fit_result_is_unaffected_by_saturation_cache() -> None:
    """SKU repetido donde todas las unidades caben: la caché de saturación nunca se
    activa (nada se agota), el resultado debe ser exactamente el mismo que sin ella."""
    space = _space(200.0, 100.0, 100.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=15)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    assert result.packed_count == 15
    assert result.unpacked_units == ()
    assert find_overlapping_placements(result.placements) == ()


def test_large_pending_quantity_keeps_same_packed_count_with_bounded_search_cost() -> None:
    """SKU repetido donde sobran muchas unidades: debe cargar exactamente la misma
    cantidad al aumentar la cantidad solicitada, sin que el costo de búsqueda (número
    de candidatos evaluados, modo diagnóstico) crezca proporcionalmente con las
    instancias pendientes -- esa es exactamente la señal de que la saturación
    temprana evita repetir la misma búsqueda cientos de veces."""
    space = _space(100.0, 50.0, 20.0)  # capacidad real: exactamente 3 (ver OPT-17)
    unit_small = make_load_unit(dimensions=_DIMS, quantity=20)
    unit_large = make_load_unit(dimensions=_DIMS, quantity=200)

    request_small = PackingRequest(
        loading_space=space, load_units=(unit_small,), diagnostic_mode=True
    )
    request_large = PackingRequest(
        loading_space=space, load_units=(unit_large,), diagnostic_mode=True
    )

    result_small = PackingEngine().optimize(request_small)
    result_large = PackingEngine().optimize(request_large)

    assert result_small.packed_count == 3
    assert result_large.packed_count == 3
    assert len(result_small.unpacked_units) == 17
    assert len(result_large.unpacked_units) == 197

    candidates_small = _candidates_generated(result_small.warnings)
    candidates_large = _candidates_generated(result_large.warnings)
    # Sin la saturación temprana, 180 instancias adicionales pendientes
    # repetirían cada una una búsqueda completa (decenas de candidatos
    # cada una); con ella, el costo extra debe ser pequeño y acotado,
    # no proporcional a la cantidad solicitada.
    assert candidates_large - candidates_small < 200

    assert find_overlapping_placements(result_large.placements) == ()


def test_saturation_of_sku_a_never_blocks_a_smaller_sku_b() -> None:
    """Dos SKU: A deja de caber tras la primera unidad, pero B (mucho más pequeño)
    sigue cabiendo en el hueco residual -- el agotamiento de A nunca puede impedir
    cargar B."""
    space = _space(200.0, 100.0, 100.0)
    unit_a = make_load_unit(
        sku="SKU-A",
        dimensions=Dimensions3D(200.0, 100.0, 80.0),
        quantity=2,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    unit_b = make_load_unit(
        sku="SKU-B",
        dimensions=Dimensions3D(50.0, 50.0, 15.0),
        quantity=3,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    request = PackingRequest(loading_space=space, load_units=(unit_a, unit_b))

    result = PackingEngine().optimize(request)

    packed_by_sku: dict[str, int] = {}
    load_units_by_id = {unit_a.id: unit_a, unit_b.id: unit_b}
    for placement in result.placements:
        sku = load_units_by_id[placement.load_unit_id].sku
        packed_by_sku[sku] = packed_by_sku.get(sku, 0) + 1

    assert packed_by_sku.get("SKU-A", 0) == 1
    assert packed_by_sku.get("SKU-B", 0) == 3
    assert find_overlapping_placements(result.placements) == ()


def test_saturation_respects_orientation_restrictions() -> None:
    """SKU con orientaciones limitadas: la instancia que agota la búsqueda respeta
    exactamente las orientaciones permitidas configuradas, nunca prueba otras."""
    space = _space(90.0, 40.0, 20.0)
    unit = make_load_unit(
        dimensions=_DIMS,
        quantity=10,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    for placement in result.placements:
        assert placement.orientation.code == OrientationCode.LWH_XYZ


def test_saturation_respects_max_stack_count() -> None:
    """Reglas de apilamiento: el límite `max_stack_count` sigue respetándose
    exactamente igual, incluso cuando la saturación temprana entra en juego."""
    space = _space(40.0, 30.0, 100.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=20, max_stack_count=2)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    assert result.packed_count == 2
    assert len(result.unpacked_units) == 18


def test_saturation_respects_individual_extinguisher_horizontality() -> None:
    """Extintores individuales >= 3 kg: siguen horizontales, eje largo paralelo a X,
    incluso cuando muchas instancias quedan pendientes tras saturar el espacio."""
    space = _space(65.0, 25.0, 25.0)
    extinguisher = make_individual_extinguisher(nominal_kg=4.0, quantity=15, max_stack_count=1)
    request = PackingRequest(loading_space=space, load_units=(extinguisher,))

    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    assert result.packed_count < 15
    for placement in result.placements:
        assert placement.orientation.code == OrientationCode.LWH_XYZ


def test_no_floating_boxes_when_saturation_cache_is_active() -> None:
    """Cero cajas flotantes: toda caja aceptada tiene soporte completo, incluso en un
    escenario que satura el espacio y activa la caché de saturación temprana."""
    space = _space(100.0, 50.0, 60.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=50)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    boxes = [box_from_placement(p) for p in result.placements]
    for index, box in enumerate(boxes):
        others = boxes[:index] + boxes[index + 1 :]
        assert is_supported(box, others, minimum_support_ratio=1.0)


def test_no_out_of_bounds_boxes_when_saturation_cache_is_active() -> None:
    """Cero cajas fuera de límites, incluso con la caché de saturación activa."""
    space = _space(100.0, 50.0, 60.0)
    unit = make_load_unit(dimensions=_DIMS, quantity=50)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    for placement in result.placements:
        box = box_from_placement(placement)
        assert fits_inside_loading_space(box, space)
