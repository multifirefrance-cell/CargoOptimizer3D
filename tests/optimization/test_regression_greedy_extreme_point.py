"""Pruebas de regresión: capturan comportamiento de referencia previo a la fase 4.2.

Estas pruebas no comprueban optimalidad matemática: fijan valores
concretos (conteos, códigos de razón, posiciones, orientaciones) del
comportamiento ya verificado como correcto de
`GreedyExtremePointStrategy`, para detectar cualquier cambio de
comportamiento introducido por futuras optimizaciones de rendimiento
(esta fase incluida: poda de candidatos, caché de bounding box,
omisión de score para candidatos rechazados). Los `LoadUnit` se
construyen frescos dentro de cada prueba (sus `id` son aleatorios por
diseño del dominio): nunca se fijan UUID literales como referencia,
solo estructura relativa (SKU, posición, orientación, conteos).
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.optimization.codes import UnpackedReason
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from tests.optimization._helpers import (
    make_grouped_extinguisher,
    make_individual_extinguisher,
    make_load_unit,
)


def test_mixed_scenario_reference_counts() -> None:
    """Escenario mixto pequeño: todo cabe, ninguna instancia queda sin colocar."""
    space = LoadingSpace(
        name="Furgón de referencia",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(200.0, 150.0, 100.0),
    )
    normal = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=6)
    extinguisher = make_individual_extinguisher(nominal_kg=5.0)
    grouped = make_grouped_extinguisher(nominal_kg=2.0, quantity=2)

    request = PackingRequest(loading_space=space, load_units=(normal, extinguisher, grouped))
    result = PackingEngine().optimize(request)

    assert result.algorithm_name == "greedy_extreme_point_v1"
    assert result.requested_count == 9
    assert result.packed_count == 9
    assert result.unpacked_units == ()

    first_placement = next(p for p in result.placements if p.sequence_number == 1)
    assert first_placement.position == Position3D(0.0, 0.0, 0.0)


def test_no_feasible_position_when_space_is_full() -> None:
    """Más instancias de las que caben: el resto se clasifica como NO_FEASIBLE_POSITION."""
    space = LoadingSpace(
        name="Caja pequeña de referencia",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(40.0, 30.0, 20.0),
    )
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=3)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 1
    assert len(result.unpacked_units) == 2
    for unpacked in result.unpacked_units:
        assert unpacked.reason_code == UnpackedReason.NO_FEASIBLE_POSITION.value


def test_loading_space_weight_exceeded_classification_is_stable() -> None:
    """Una única instancia, sin otros placements: el único fallo posible es el peso.

    Escenario aislado deliberadamente (una sola instancia, espacio
    vacío) para que el único candidato evaluado (el origen) no colisione
    con nada ni quede podado por `pruning.py` (el origen nunca es
    estrictamente interior a una caja existente porque no hay ninguna):
    la única violación posible es el peso, así que la clasificación
    debe seguir siendo exactamente `LOADING_SPACE_WEIGHT_EXCEEDED`, no
    `NO_FEASIBLE_POSITION`.
    """
    space = LoadingSpace(
        name="Bodega con límite de peso",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(1000.0, 1000.0, 200.0),
        max_weight_kg=50.0,
    )
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), weight_kg=100.0, quantity=1)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 0
    assert len(result.unpacked_units) == 1
    assert (
        result.unpacked_units[0].reason_code == UnpackedReason.LOADING_SPACE_WEIGHT_EXCEEDED.value
    )


def test_determinism_across_repeated_runs() -> None:
    space = LoadingSpace(
        name="Bodega de determinismo",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(300.0, 200.0, 150.0),
    )
    normal = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=10)
    extinguisher = make_individual_extinguisher(nominal_kg=5.0, quantity=2)
    request = PackingRequest(loading_space=space, load_units=(normal, extinguisher))
    engine = PackingEngine()

    result_a = engine.optimize(request)
    result_b = engine.optimize(request)

    assert result_a.placements == result_b.placements
    assert result_a.unpacked_units == result_b.unpacked_units
    assert result_a.packed_count == result_b.packed_count
