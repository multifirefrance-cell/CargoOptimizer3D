"""`SceneController`: posee el `Plotter` de PyVista y los actores de la escena.

Responsabilidades, y solo estas (ver `docs/ThreeDViewerDesign.md`,
sección 3.1): cargar un `SceneModel`, crear/eliminar actores,
visibilidad, selección, cámara, tema, limpieza de recursos. No decide
qué mostrar (eso lo decide `SceneBuilder`, que produce el
`SceneModel`) ni sabe nada de widgets Qt (`widget.py` es quien conoce
`QWidget`/señales — este módulo recibe cualquier objeto con la misma
API que `pyvista.Plotter`, tanto un `QtInteractor` real como un
`Plotter(off_screen=True)` de pruebas).

Cámara y picking en 6.1 se resuelven aquí mismo (encuadre automático +
picking por actor); no se extraen `camera_controller.py`/
`picking_controller.py` todavía porque, con actor-por-caja, ninguno de
los dos justifica un archivo propio — ver la nota de la sección 3.1 del
diseño sobre cuándo sí haría falta.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import pyvista as pv

from cargo_optimizer.domain.enums import DoorPosition
from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry
from cargo_optimizer.presentation.desktop.viewer.constants import (
    BOX_EDGE_LINE_WIDTH,
    BOX_OPACITY,
    DOOR_HIGHLIGHT_LINE_WIDTH,
    FLOOR_OPACITY,
    SELECTION_LINE_WIDTH,
    THEME_LIGHT,
    WALL_OPACITY,
    WIREFRAME_LINE_WIDTH,
    theme_colors,
)
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel, SceneModel


class PyVistaPlotterLike(Protocol):
    """Lo que `SceneController` necesita de un `Plotter`/`QtInteractor` de PyVista.

    Protocolo estructural deliberado (mismo criterio que
    `PackingStrategy` en `optimization`, ADR-0008): no importa si el
    objeto real es un `pyvistaqt.QtInteractor` (producción) o un
    `pyvista.Plotter(off_screen=True)` (pruebas) — ver
    `docs/ThreeDViewerDesign.md`, sección 22, sobre por qué `QtInteractor`
    no es seguro de instanciar bajo la plataforma Qt "offscreen".
    """

    background_color: Any

    def add_mesh(self, mesh: Any, **kwargs: Any) -> Any: ...
    def remove_actor(self, actor: Any, render: bool = True) -> bool: ...
    def reset_camera(self, render: bool = True, bounds: Any = None) -> None: ...
    def view_isometric(self) -> None: ...
    def view_xy(self) -> None: ...
    def view_yz(self) -> None: ...
    def view_xz(self) -> None: ...
    def render(self) -> None: ...
    def enable_mesh_picking(self, **kwargs: Any) -> Any: ...
    def disable_picking(self) -> None: ...
    def close(self) -> None: ...
    def screenshot(self, filename: Any = None, **kwargs: Any) -> Any: ...
    def add_camera_orientation_widget(self, **kwargs: Any) -> Any: ...

    @property
    def camera(self) -> Any: ...


def cube_center_and_lengths(
    position: tuple[float, float, float], dimensions: tuple[float, float, float]
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Convierte esquina mínima + dimensiones orientadas al centro y longitudes que espera PyVista.

    Debe cumplir exactamente `max_x = position[0] + dimensions[0]` (e
    igual para Y/Z): PyVista construye cubos por centro, pero
    `Placement` expresa su esquina de origen (mínima) — ver
    `docs/ThreeDViewerDesign.md`, sección 9, y el encargo de la fase
    6.1, sección 10.
    """
    px, py, pz = position
    dx, dy, dz = dimensions
    center = (px + dx / 2.0, py + dy / 2.0, pz + dz / 2.0)
    return center, (dx, dy, dz)


_DOOR_FACE_BY_POSITION: dict[DoorPosition, str] = {
    DoorPosition.FRONT: "max_x",
    DoorPosition.REAR: "min_x",
    DoorPosition.LEFT: "min_y",
    DoorPosition.RIGHT: "max_y",
    DoorPosition.TOP: "max_z",
}


class SceneController:
    """Dueño del `Plotter` y de todos los actores de la escena 3D actual."""

    def __init__(self, plotter: PyVistaPlotterLike, theme: str = THEME_LIGHT) -> None:
        self._plotter = plotter
        self._theme = theme
        self._scene: SceneModel | None = None
        self._box_actors: dict[int, Any] = {}  # sequence_number -> actor
        self._sequence_number_by_actor_id: dict[int, int] = {}  # id(actor) -> sequence_number
        self._container_actors: list[Any] = []
        self._axes_actors: list[Any] = []
        self._selected_sequence_number: int | None = None
        self._on_selection_changed: Callable[[int | None], None] | None = None
        self.apply_theme(theme)
        # Cubo de orientación: infraestructura ya disponible de fábrica en
        # PyVista (`add_camera_orientation_widget`), sin arquitectura
        # nueva — orienta al usuario sobre qué cara mira la cámara en todo
        # momento (rediseño UX, "nunca esconderse detrás de paneles").
        self._plotter.add_camera_orientation_widget()

    def set_selection_changed_callback(self, callback: Callable[[int | None], None] | None) -> None:
        """Se invoca únicamente cuando la selección cambia por un clic del usuario (picking)."""
        self._on_selection_changed = callback

    # ------------------------------------------------------------------
    # Ciclo de vida de la escena
    # ------------------------------------------------------------------

    def load_scene(self, scene: SceneModel) -> None:
        self.clear_scene()
        self._scene = scene
        self._build_container(scene)
        self._build_boxes(scene)
        self._build_axes(scene)
        self._enable_picking()
        self.set_container_visible(scene.container_visible)
        self.set_boxes_visible(scene.boxes_visible)
        self.set_axes_visible(scene.axes_visible)
        if scene.selected_sequence_number is not None:
            self._apply_selection(scene.selected_sequence_number)
        self.reset_camera()

    def clear_scene(self) -> None:
        for actor in list(self._box_actors.values()):
            self._plotter.remove_actor(actor, render=False)
        for actor in self._container_actors:
            self._plotter.remove_actor(actor, render=False)
        for actor in self._axes_actors:
            self._plotter.remove_actor(actor, render=False)
        self._box_actors.clear()
        self._sequence_number_by_actor_id.clear()
        self._container_actors.clear()
        self._axes_actors.clear()
        self._selected_sequence_number = None
        self._scene = None
        self._plotter.render()

    def close(self) -> None:
        """Libera el `Plotter` (fin del ciclo de vida — ver `widget.py::closeEvent`)."""
        self.clear_scene()
        self._plotter.close()

    def export_screenshot_png(self) -> bytes | None:
        """PNG en memoria de la vista actual, o `None` si la captura falla por cualquier motivo.

        Escribe a un archivo temporal (mismo mecanismo que
        `Plotter.screenshot(filename)`, que ya sabe codificar PNG) y lee
        los bytes de vuelta — evita que `viewer/` tenga que depender
        directamente de Pillow/imageio para codificar la imagen él
        mismo. Uso previsto: `infrastructure/pdf` (fase 9.1, ver
        `docs/PdfReportDesign.md`, sección 6) recibe estos bytes ya
        capturados, nunca genera la imagen por su cuenta.
        """
        fd, tmp_name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            self._plotter.screenshot(str(tmp_path))
            return tmp_path.read_bytes()
        except Exception:  # noqa: BLE001 - un fallo de captura nunca debe propagarse
            return None
        finally:
            tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build_container(self, scene: SceneModel) -> None:
        colors = theme_colors(self._theme)
        dims = scene.loading_space.internal_dimensions
        length, width, height = dims.length_cm, dims.width_cm, dims.height_cm

        floor = pv.Plane(
            center=(length / 2.0, width / 2.0, 0.0),
            direction=(0.0, 0.0, 1.0),
            i_size=length,
            j_size=width,
        )
        self._container_actors.append(
            self._plotter.add_mesh(
                floor, color=colors["floor"], opacity=FLOOR_OPACITY, name="viewer-floor"
            )
        )

        wall_specs = (
            ((length / 2.0, 0.0, height / 2.0), (0.0, 1.0, 0.0), length, height),
            ((length / 2.0, width, height / 2.0), (0.0, 1.0, 0.0), length, height),
            ((0.0, width / 2.0, height / 2.0), (1.0, 0.0, 0.0), width, height),
            ((length, width / 2.0, height / 2.0), (1.0, 0.0, 0.0), width, height),
        )
        for center, direction, i_size, j_size in wall_specs:
            wall = pv.Plane(center=center, direction=direction, i_size=i_size, j_size=j_size)
            self._container_actors.append(
                self._plotter.add_mesh(
                    wall, color=colors["wall"], opacity=WALL_OPACITY, name="viewer-wall"
                )
            )

        wireframe = pv.Box(bounds=(0.0, length, 0.0, width, 0.0, height))
        self._container_actors.append(
            self._plotter.add_mesh(
                wireframe,
                style="wireframe",
                color=colors["edge"],
                line_width=WIREFRAME_LINE_WIDTH,
                name="viewer-wireframe",
            )
        )

        door_actor = self._build_door_highlight(scene, length, width, height, colors)
        if door_actor is not None:
            self._container_actors.append(door_actor)

    def _build_door_highlight(
        self,
        scene: SceneModel,
        length: float,
        width: float,
        height: float,
        colors: dict[str, str],
    ) -> Any | None:
        face = _DOOR_FACE_BY_POSITION.get(scene.loading_space.door_position)
        if face is None:
            # DoorPosition.UNRESTRICTED (u otro valor sin cara única): representación
            # neutra, sin resaltar ninguna cara — ver encargo de fase 6.1, sección 8.
            return None

        face_specs: dict[
            str, tuple[tuple[float, float, float], tuple[float, float, float], float, float]
        ] = {
            "min_x": ((0.0, width / 2.0, height / 2.0), (1.0, 0.0, 0.0), width, height),
            "max_x": ((length, width / 2.0, height / 2.0), (1.0, 0.0, 0.0), width, height),
            "min_y": ((length / 2.0, 0.0, height / 2.0), (0.0, 1.0, 0.0), length, height),
            "max_y": ((length / 2.0, width, height / 2.0), (0.0, 1.0, 0.0), length, height),
            "max_z": ((length / 2.0, width / 2.0, height), (0.0, 0.0, 1.0), length, width),
        }
        center, direction, i_size, j_size = face_specs[face]
        rectangle = pv.Plane(center=center, direction=direction, i_size=i_size, j_size=j_size)

        return self._plotter.add_mesh(
            rectangle,
            style="wireframe",
            color=colors["door_highlight"],
            line_width=DOOR_HIGHLIGHT_LINE_WIDTH,
            name="viewer-door",
        )

    def _build_boxes(self, scene: SceneModel) -> None:
        for visual in scene.placement_visuals:
            center, lengths = cube_center_and_lengths(visual.position, visual.oriented_dimensions)
            mesh = pv.Cube(
                center=center, x_length=lengths[0], y_length=lengths[1], z_length=lengths[2]
            )
            actor = self._plotter.add_mesh(
                mesh,
                color=visual.color_hex,
                opacity=BOX_OPACITY,
                show_edges=True,
                edge_color=ColorRegistry.edge_color(self._theme),
                line_width=BOX_EDGE_LINE_WIDTH,
                name=f"viewer-box-{visual.sequence_number}",
            )
            self._box_actors[visual.sequence_number] = actor
            self._sequence_number_by_actor_id[id(actor)] = visual.sequence_number

    def _build_axes(self, scene: SceneModel) -> None:
        colors = theme_colors(self._theme)
        dims = scene.loading_space.internal_dimensions
        origin = (0.0, 0.0, 0.0)
        axis_specs = (
            ((dims.length_cm, 0.0, 0.0), colors["axis_x"]),
            ((0.0, dims.width_cm, 0.0), colors["axis_y"]),
            ((0.0, 0.0, dims.height_cm), colors["axis_z"]),
        )
        for endpoint, color in axis_specs:
            line = pv.Line(origin, endpoint)
            self._axes_actors.append(
                self._plotter.add_mesh(
                    line, color=color, line_width=WIREFRAME_LINE_WIDTH, name="viewer-axis"
                )
            )

    # ------------------------------------------------------------------
    # Visibilidad
    # ------------------------------------------------------------------

    def set_container_visible(self, visible: bool) -> None:
        for actor in self._container_actors:
            actor.visibility = visible
        self._plotter.render()

    def set_boxes_visible(self, visible: bool) -> None:
        for actor in self._box_actors.values():
            actor.visibility = visible
        self._plotter.render()

    def set_axes_visible(self, visible: bool) -> None:
        for actor in self._axes_actors:
            actor.visibility = visible
        self._plotter.render()

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------

    def set_selected_placement(self, sequence_number: int | None) -> None:
        """Actualiza la selección visual sin emitir ninguna notificación (uso externo)."""
        self._apply_selection(sequence_number)

    def _apply_selection(self, sequence_number: int | None) -> None:
        if self._selected_sequence_number is not None:
            previous = self._box_actors.get(self._selected_sequence_number)
            if previous is not None:
                previous.prop.line_width = BOX_EDGE_LINE_WIDTH
                previous.prop.edge_color = ColorRegistry.edge_color(self._theme)

        self._selected_sequence_number = sequence_number

        if sequence_number is not None:
            actor = self._box_actors.get(sequence_number)
            if actor is not None:
                actor.prop.line_width = SELECTION_LINE_WIDTH
                actor.prop.edge_color = ColorRegistry.selection_color(self._theme)

        self._plotter.render()

    def _enable_picking(self) -> None:
        # Idempotente: `load_scene` puede llamarse varias veces (nuevo resultado,
        # cambio de tema) sobre el mismo Plotter, y PyVista no permite activar el
        # picking dos veces sin desactivarlo primero.
        self._plotter.disable_picking()
        self._plotter.enable_mesh_picking(
            callback=self._handle_pick,
            use_actor=True,
            show=False,
            show_message=False,
            left_clicking=True,
        )

    def _handle_pick(self, actor: Any) -> None:
        sequence_number = (
            None if actor is None else self._sequence_number_by_actor_id.get(id(actor))
        )
        self._apply_selection(sequence_number)
        if self._on_selection_changed is not None:
            self._on_selection_changed(sequence_number)

    def find_placement_actor(self, sequence_number: int) -> Any | None:
        return self._box_actors.get(sequence_number)

    def find_placement_visual(self, sequence_number: int) -> PlacementVisualModel | None:
        """El `PlacementVisualModel` de la escena actual con ese `sequence_number`, si existe."""
        if self._scene is None:
            return None
        for visual in self._scene.placement_visuals:
            if visual.sequence_number == sequence_number:
                return visual
        return None

    # ------------------------------------------------------------------
    # Cámara
    # ------------------------------------------------------------------

    def reset_camera(self) -> None:
        self._plotter.view_isometric()
        self._plotter.camera.up = (0.0, 0.0, 1.0)
        self._plotter.reset_camera()
        self._plotter.render()

    def view_front(self) -> None:
        """Vista frontal: mirando a lo largo del eje X (ancho x alto, plano Y-Z)."""
        self._plotter.view_yz()
        self._plotter.reset_camera()
        self._plotter.render()

    def view_top(self) -> None:
        """Vista superior: mirando hacia abajo por el eje Z (largo x ancho, plano X-Y)."""
        self._plotter.view_xy()
        self._plotter.reset_camera()
        self._plotter.render()

    def view_side(self) -> None:
        """Vista lateral: mirando a lo largo del eje Y (largo x alto, plano X-Z)."""
        self._plotter.view_xz()
        self._plotter.reset_camera()
        self._plotter.render()

    def focus_placement(self, sequence_number: int) -> None:
        """Encuadra la cámara sobre una única caja. No hace nada si no existe."""
        actor = self._box_actors.get(sequence_number)
        if actor is None:
            return
        self._plotter.reset_camera(bounds=actor.GetBounds())
        self._plotter.render()

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def apply_theme(self, theme: str) -> None:
        self._theme = theme
        colors = theme_colors(theme)
        self._plotter.background_color = colors["background"]
        if self._scene is not None:
            self.load_scene(self._scene)
        else:
            self._plotter.render()
