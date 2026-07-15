"""Pruebas de integración: dominio + geometría + reglas + optimización juntos.

No afirman optimalidad matemática de ninguna solución: solo corrección
(sin colisiones, dentro de límites, reglas respetadas), determinismo y
que la API pública funciona tal como se documenta.
"""

from __future__ import annotations

from cargo_optimizer import LoadingSpace, LoadUnit, PackingEngine, PackingRequest
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.collision import find_overlapping_placements
from cargo_optimizer.geometry.layout_validation import validate_layout
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.engine import RulesEngine


def _assert_result_is_coherent(result, loading_space, load_units_by_id) -> None:  # type: ignore[no-untyped-def]
    assert result.packed_count + len(result.unpacked_units) == result.requested_count
    assert find_overlapping_placements(result.placements) == ()
    for placement in result.placements:
        box = box_from_placement(placement)
        assert fits_inside_loading_space(box, loading_space)

    validation = validate_layout(loading_space, result.placements)
    assert validation.is_valid, validation.issues

    rules_engine = RulesEngine()
    for placement in result.placements:
        unit = load_units_by_id[placement.load_unit_id]
        other_placements = tuple(p for p in result.placements if p is not placement)
        context = PlacementRuleContext(
            loading_space=loading_space,
            load_unit=unit,
            candidate_position=placement.position,
            candidate_orientation=placement.orientation,
            existing_placements=other_placements,
            load_units_by_id=load_units_by_id,
        )
        evaluation = rules_engine.evaluate_placement(context)
        assert evaluation.is_allowed, evaluation.errors


def test_public_api_from_cargo_optimizer_root() -> None:
    space = LoadingSpace(
        name="Espacio personalizado",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(150.0, 80.0, 90.0),
    )
    unit = LoadUnit(
        sku="MIXED-1",
        name="Caja",
        dimensions=Dimensions3D(30.0, 20.0, 15.0),
        weight_kg=8.0,
        quantity=6,
    )
    request = PackingRequest(loading_space=space, load_units=(unit,))
    engine = PackingEngine()
    result = engine.optimize(request)

    assert result.packed_count > 0
    _assert_result_is_coherent(result, space, {unit.id: unit})


def test_standard_20ft_container() -> None:
    space = LoadingSpace.standard_20ft_container()
    unit = LoadUnit(
        sku="PALLET-1",
        name="Pallet estándar",
        dimensions=Dimensions3D(120.0, 100.0, 100.0),
        weight_kg=250.0,
        quantity=10,
    )
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    _assert_result_is_coherent(result, space, {unit.id: unit})


def test_custom_truck() -> None:
    truck = LoadingSpace(
        name="Camión rígido 3.5T",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(420.0, 210.0, 220.0),
        max_weight_kg=1500.0,
    )
    unit = LoadUnit(
        sku="BOX-TRUCK",
        name="Caja de reparto",
        dimensions=Dimensions3D(50.0, 40.0, 30.0),
        weight_kg=15.0,
        quantity=15,
    )
    request = PackingRequest(loading_space=truck, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    _assert_result_is_coherent(result, truck, {unit.id: unit})


def test_custom_warehouse() -> None:
    warehouse = LoadingSpace(
        name="Bodega de almacenamiento",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(1000.0, 800.0, 400.0),
    )
    unit = LoadUnit(
        sku="DRUM-1",
        name="Tambor industrial",
        dimensions=Dimensions3D(60.0, 60.0, 90.0),
        weight_kg=180.0,
        quantity=20,
        max_stack_count=2,
    )
    request = PackingRequest(loading_space=warehouse, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    _assert_result_is_coherent(result, warehouse, {unit.id: unit})


def test_project_with_several_skus() -> None:
    space = LoadingSpace.standard_40ft_container()
    unit_a = LoadUnit(
        sku="A",
        name="Caja A",
        dimensions=Dimensions3D(60.0, 40.0, 40.0),
        weight_kg=30.0,
        quantity=8,
    )
    unit_b = LoadUnit(
        sku="B",
        name="Caja B",
        dimensions=Dimensions3D(40.0, 40.0, 30.0),
        weight_kg=20.0,
        quantity=8,
    )
    unit_c = LoadUnit(
        sku="C",
        name="Caja C",
        dimensions=Dimensions3D(30.0, 30.0, 30.0),
        weight_kg=10.0,
        quantity=8,
    )
    request = PackingRequest(loading_space=space, load_units=(unit_a, unit_b, unit_c))
    result = PackingEngine().optimize(request)

    assert result.packed_count > 0
    load_units_by_id = {unit_a.id: unit_a, unit_b.id: unit_b, unit_c.id: unit_c}
    _assert_result_is_coherent(result, space, load_units_by_id)


def test_result_is_deterministic_across_full_stack() -> None:
    space = LoadingSpace.standard_20ft_container()
    unit = LoadUnit(
        sku="DET-1",
        name="Caja",
        dimensions=Dimensions3D(50.0, 40.0, 30.0),
        weight_kg=20.0,
        quantity=12,
    )
    request = PackingRequest(loading_space=space, load_units=(unit,))
    engine = PackingEngine()

    result_a = engine.optimize(request)
    result_b = engine.optimize(request)

    assert result_a.placements == result_b.placements
    assert result_a.unpacked_units == result_b.unpacked_units
    assert result_a.packed_count == result_b.packed_count
