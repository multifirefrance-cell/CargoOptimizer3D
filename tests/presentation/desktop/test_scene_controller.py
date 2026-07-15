"""Pruebas de `SceneController` con un `pyvista.Plotter(off_screen=True)` real.

Deliberadamente **no** usa `pyvistaqt.QtInteractor`: bajo la plataforma
Qt `offscreen` (la que usa toda esta suite), `QtInteractor` provoca un
segmentation fault nativo de VTK en Windows (ver
`docs/ThreeDViewer.md`, sección "problemas conocidos", y
`viewer/widget.py`) — no es un fallo Python capturable. Un
`pv.Plotter(off_screen=True)` normal sí funciona de forma segura y
determinista bajo esa misma plataforma, y `SceneController` está
diseñado exactamente para aceptar cualquier objeto con esa API
(`PyVistaPlotterLike`, protocolo estructural) — así que estas pruebas
ejercitan la lógica real de construcción de escena, visibilidad,
selección y cámara contra VTK de verdad, sin ningún riesgo de bloqueo.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pyvista as pv

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.viewer.constants import THEME_DARK, THEME_LIGHT
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel, SceneModel
from cargo_optimizer.presentation.desktop.viewer.scene_controller import (
    SceneController,
    cube_center_and_lengths,
)

_SPACE = LoadingSpace(
    name="Bodega de pruebas",
    category=LoadingSpaceCategory.WAREHOUSE,
    internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
    door_position=DoorPosition.FRONT,
)


def _visual(sequence_number: int, x: float = 0.0) -> PlacementVisualModel:
    return PlacementVisualModel(
        sequence_number=sequence_number,
        instance_number=sequence_number,
        load_unit_id=uuid4(),
        sku=f"BOX-{sequence_number}",
        name="Caja",
        position=(x, 0.0, 0.0),
        oriented_dimensions=(40.0, 30.0, 20.0),
        orientation_code="lwh_xyz",
        weight_kg=10.0,
        package_type="individual",
        units_per_package=1,
        is_extinguisher=False,
        extinguisher_nominal_kg=None,
        fragile=False,
        max_stack_count=1,
        notes="",
        color_hex="#4C78A8",
    )


def _scene(count: int = 2) -> SceneModel:
    visuals = tuple(_visual(i + 1, x=i * 40.0) for i in range(count))
    return SceneModel(loading_space=_SPACE, placement_visuals=visuals)


@pytest.fixture
def plotter():  # type: ignore[no-untyped-def]
    p = pv.Plotter(off_screen=True)
    yield p
    p.close()


def test_cube_center_and_lengths_matches_min_corner_convention() -> None:
    position = (10.0, 20.0, 30.0)
    dimensions = (40.0, 30.0, 20.0)
    center, lengths = cube_center_and_lengths(position, dimensions)

    min_x, min_y, min_z = position
    max_x, max_y, max_z = (min_x + dimensions[0], min_y + dimensions[1], min_z + dimensions[2])

    assert lengths == dimensions
    assert center[0] - lengths[0] / 2.0 == pytest.approx(min_x)
    assert center[0] + lengths[0] / 2.0 == pytest.approx(max_x)
    assert center[1] - lengths[1] / 2.0 == pytest.approx(min_y)
    assert center[1] + lengths[1] / 2.0 == pytest.approx(max_y)
    assert center[2] - lengths[2] / 2.0 == pytest.approx(min_z)
    assert center[2] + lengths[2] / 2.0 == pytest.approx(max_z)


def test_cube_center_and_lengths_zero_origin() -> None:
    center, lengths = cube_center_and_lengths((0.0, 0.0, 0.0), (40.0, 30.0, 20.0))
    assert center == (20.0, 15.0, 10.0)
    assert lengths == (40.0, 30.0, 20.0)


def test_load_scene_creates_one_actor_per_box(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=3))
    assert len(controller._box_actors) == 3
    assert len(controller._container_actors) > 0
    assert len(controller._axes_actors) == 3


def test_load_scene_with_empty_placements_still_builds_container(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=0))
    assert len(controller._box_actors) == 0
    assert len(controller._container_actors) > 0


def test_clear_scene_removes_all_actors(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=2))
    controller.clear_scene()
    assert controller._box_actors == {}
    assert controller._container_actors == []
    assert controller._axes_actors == []


def test_set_boxes_visible_toggles_actor_visibility(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=2))
    controller.set_boxes_visible(False)
    assert all(not actor.visibility for actor in controller._box_actors.values())
    controller.set_boxes_visible(True)
    assert all(actor.visibility for actor in controller._box_actors.values())


def test_set_container_visible_toggles_container_actors(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=1))
    controller.set_container_visible(False)
    assert all(not actor.visibility for actor in controller._container_actors)


def test_set_axes_visible_toggles_axes_actors(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=1))
    controller.set_axes_visible(False)
    assert all(not actor.visibility for actor in controller._axes_actors)


def test_set_selected_placement_highlights_actor_without_callback(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    received: list[int | None] = []
    controller.set_selection_changed_callback(received.append)
    controller.load_scene(_scene(count=2))

    controller.set_selected_placement(1)

    assert controller._selected_sequence_number == 1
    assert received == []  # llamada externa: nunca notifica


def test_picking_callback_selects_and_notifies(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    received: list[int | None] = []
    controller.set_selection_changed_callback(received.append)
    controller.load_scene(_scene(count=2))

    actor = controller.find_placement_actor(2)
    assert actor is not None
    controller._handle_pick(actor)

    assert controller._selected_sequence_number == 2
    assert received == [2]


def test_picking_callback_with_none_actor_deselects(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    received: list[int | None] = []
    controller.set_selection_changed_callback(received.append)
    controller.load_scene(_scene(count=2))
    controller.set_selected_placement(1)

    controller._handle_pick(None)

    assert controller._selected_sequence_number is None
    assert received == [None]


def test_find_placement_visual_returns_matching_model(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=2))
    visual = controller.find_placement_visual(2)
    assert visual is not None
    assert visual.sequence_number == 2
    assert controller.find_placement_visual(999) is None


def test_reset_camera_does_not_raise_on_empty_scene(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=0))
    controller.reset_camera()  # no debe lanzar excepción


def test_focus_placement_on_unknown_sequence_is_a_no_op(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=1))
    controller.focus_placement(999)  # no debe lanzar excepción


def test_apply_theme_rebuilds_scene_when_one_is_loaded(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=2))
    controller.apply_theme(THEME_DARK)
    assert len(controller._box_actors) == 2  # reconstruida, no perdida


def test_apply_theme_without_scene_does_not_raise(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.apply_theme(THEME_LIGHT)  # no debe lanzar excepción


def test_load_scene_twice_does_not_duplicate_picking(plotter) -> None:  # type: ignore[no-untyped-def]
    controller = SceneController(plotter)
    controller.load_scene(_scene(count=1))
    controller.load_scene(_scene(count=1))  # no debe lanzar PyVistaPickingError


def test_close_releases_the_plotter() -> None:
    # Plotter propio, no el de la fixture: `close()` lo cierra, y la fixture
    # 'plotter' intentaría cerrarlo de nuevo en su teardown si lo compartiera.
    own_plotter = pv.Plotter(off_screen=True)
    controller = SceneController(own_plotter)
    controller.load_scene(_scene(count=1))
    controller.close()
    assert controller._box_actors == {}
