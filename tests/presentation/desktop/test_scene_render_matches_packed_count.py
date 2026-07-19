"""Integración motor -> visor 3D (fase OPT-18, Parte 4, punto 10).

Verifica que el número de cajas representadas en la escena 3D (tanto
en `SceneModel.placement_visuals` como, tras cargarla en
`SceneController`, el número de registros por caja) sea exactamente
el número de cajas realmente cargadas por el motor (`packed_count`) --
ni una más, ni una menos -- incluso con la agrupación de actores por
forma+color introducida en esta fase.
"""

from __future__ import annotations

import pyvista as pv

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from cargo_optimizer.presentation.desktop.viewer.scene_builder import SceneBuilder
from cargo_optimizer.presentation.desktop.viewer.scene_controller import SceneController
from tests.optimization._helpers import make_load_unit


def test_rendered_box_count_matches_packed_count_single_sku() -> None:
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(200.0, 100.0, 100.0),
    )
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=15)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    load_units_by_id = {unit.id: unit}

    scene = SceneBuilder().build(result, load_units_by_id)
    assert len(scene.placement_visuals) == result.packed_count

    plotter = pv.Plotter(off_screen=True)
    controller = SceneController(plotter)
    controller.load_scene(scene)
    try:
        assert len(controller._box_records) == result.packed_count
    finally:
        controller.close()


def test_rendered_box_count_matches_packed_count_with_partial_saturation() -> None:
    """Escenario con unidades pendientes (saturación, fase OPT-18 Parte B): el visor
    solo debe representar las cajas realmente cargadas, nunca las pendientes."""
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(100.0, 50.0, 20.0),
    )
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=50)
    request = PackingRequest(loading_space=space, load_units=(unit,))
    result = PackingEngine().optimize(request)
    load_units_by_id = {unit.id: unit}

    assert result.packed_count < 50
    assert len(result.unpacked_units) > 0

    scene = SceneBuilder().build(result, load_units_by_id)
    assert len(scene.placement_visuals) == result.packed_count

    plotter = pv.Plotter(off_screen=True)
    controller = SceneController(plotter)
    controller.load_scene(scene)
    try:
        assert len(controller._box_records) == result.packed_count
    finally:
        controller.close()


def test_rendered_box_count_matches_packed_count_with_multiple_skus_and_groups() -> None:
    """Varios SKU con distinta forma/color caen en grupos/actores distintos, pero el
    total de cajas representadas sigue siendo exactamente `packed_count`."""
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(200.0, 100.0, 100.0),
    )
    unit_a = make_load_unit(
        sku="SKU-A",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        quantity=8,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    unit_b = make_load_unit(
        sku="SKU-B",
        dimensions=Dimensions3D(20.0, 20.0, 20.0),
        quantity=8,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
    )
    request = PackingRequest(loading_space=space, load_units=(unit_a, unit_b))
    result = PackingEngine().optimize(request)
    load_units_by_id = {unit_a.id: unit_a, unit_b.id: unit_b}

    scene = SceneBuilder().build(result, load_units_by_id)
    assert len(scene.placement_visuals) == result.packed_count

    plotter = pv.Plotter(off_screen=True)
    controller = SceneController(plotter)
    controller.load_scene(scene)
    try:
        assert len(controller._box_records) == result.packed_count
        assert len(controller._group_actors) <= 2  # como mucho un grupo por SKU
    finally:
        controller.close()
