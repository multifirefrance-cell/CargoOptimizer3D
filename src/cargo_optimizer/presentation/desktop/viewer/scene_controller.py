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

**Fase OPT-18 (agrupación de cajas por forma+color)**: la estrategia
"un actor por caja" de la fase 6.1 (ver CLAUDE.md, invariante del
visor 3D) se sustituye por "un actor por grupo de cajas visualmente
idénticas" — mismas dimensiones orientadas y mismo color (`color_hex`),
es decir, mismo SKU en la misma orientación. Cada grupo se construye
como una única malla combinada (`pyvista.merge`, `merge_points=False`
para no fusionar vértices coincidentes entre cajas que se tocan y
alterar sutilmente el resultado visual) en vez de una caja por
`add_mesh`. Con miles de cajas del mismo SKU (el caso real que motiva
esta fase), esto reduce el número de actores VTK de "uno por caja" a
"uno por SKU/orientación distintos", el factor dominante en el tiempo
de `SceneController.load_scene` medido en `docs/ThreeDViewer.md`,
sección 12.

La selección ya no puede resolverse por identidad de actor (varias
cajas comparten uno): `_box_records` guarda el centro y las longitudes
de cada caja por `sequence_number`, y el picking (todavía por actor,
`enable_mesh_picking(use_actor=True)`, sin tocar VTK de más bajo nivel)
resuelve la caja concreta dentro del grupo clicado por la posición
mundial del click (`Plotter.picked_point`) más cercana al centro de
cada caja del grupo — nunca por índice de celda/punto de VTK, para no
depender de la topología interna de la malla combinada. El resaltado
de selección ya no cambia las propiedades del actor compartido (eso
recolorearía/marcaría todas las cajas del grupo a la vez): se
construye un actor de contorno independiente
(`self._selection_actor`), una única caja en modo wireframe sobre la
caja seleccionada, añadido/eliminado solo cuando cambia la selección —
el color de relleno del grupo nunca se toca, igual que exigía la
estrategia anterior.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
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

_GroupKey = tuple[tuple[float, float, float], str]
"""Clave de agrupación visual: (dimensiones orientadas, color_hex). Dos cajas con la
misma clave son geométricamente indistinguibles salvo por su posición, así que
comparten un único actor/malla combinada."""


@dataclass(slots=True)
class _BoxRecord:
    """Metadatos de una caja individual dentro de una malla combinada por grupo."""

    group_key: _GroupKey
    center: tuple[float, float, float]
    lengths: tuple[float, float, float]


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
    def add_point_labels(self, points: Any, labels: Any, **kwargs: Any) -> Any: ...
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
        self._group_actors: dict[_GroupKey, Any] = {}  # (dims, color) -> actor de malla combinada
        self._actor_group_by_id: dict[int, _GroupKey] = {}  # id(actor) -> clave de grupo
        self._box_records: dict[int, _BoxRecord] = {}  # sequence_number -> centro/longitudes
        self._group_members: dict[_GroupKey, list[int]] = {}  # clave de grupo -> sequence_number
        self._sku_groups: dict[str, list[_GroupKey]] = {}  # sku -> claves de grupo que le pertenecen
        self._sku_label_actors: dict[str, list[Any]] = {}  # sku -> lista de actores de texto
        self._selection_actor: Any | None = None  # contorno de resalte, independiente del grupo
        self._container_actors: list[Any] = []
        self._axes_actors: list[Any] = []
        self._label_actors: list[Any] = []
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
        for actor in list(self._group_actors.values()):
            self._plotter.remove_actor(actor, render=False)
        if self._selection_actor is not None:
            self._plotter.remove_actor(self._selection_actor, render=False)
            self._selection_actor = None
        for actor in self._container_actors:
            self._plotter.remove_actor(actor, render=False)
        for actor in self._axes_actors:
            self._plotter.remove_actor(actor, render=False)
        for actor in self._label_actors:
            self._plotter.remove_actor(actor, render=False)
        self._group_actors.clear()
        self._actor_group_by_id.clear()
        self._box_records.clear()
        self._group_members.clear()
        self._sku_groups.clear()
        self._sku_label_actors.clear()
        self._container_actors.clear()
        self._axes_actors.clear()
        self._label_actors.clear()
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
        """Agrupa cajas visualmente idénticas (mismas dimensiones orientadas y mismo
        color) en una única malla combinada por grupo -- ver docstring del módulo
        (fase OPT-18). El orden de construcción no importa para la corrección: cada
        caja mantiene su propio `_BoxRecord` (centro, longitudes) indexado por
        `sequence_number`, independientemente de a qué grupo/actor pertenezca.
        """
        import numpy as np  # noqa: PLC0415 - numpy garantizado por dependencia de pyvista

        groups: dict[_GroupKey, list[PlacementVisualModel]] = {}
        for visual in scene.placement_visuals:
            key: _GroupKey = (visual.oriented_dimensions, visual.color_hex)
            groups.setdefault(key, []).append(visual)
            center, lengths = cube_center_and_lengths(visual.position, visual.oriented_dimensions)
            self._box_records[visual.sequence_number] = _BoxRecord(
                group_key=key, center=center, lengths=lengths
            )
            self._group_members.setdefault(key, []).append(visual.sequence_number)
            if key not in self._sku_groups.get(visual.sku, []):
                self._sku_groups.setdefault(visual.sku, [])
                if key not in self._sku_groups[visual.sku]:
                    self._sku_groups[visual.sku].append(key)

        for group_index, (key, visuals) in enumerate(groups.items()):
            _dimensions, color_hex = key
            cubes = [
                pv.Cube(
                    center=self._box_records[visual.sequence_number].center,
                    x_length=self._box_records[visual.sequence_number].lengths[0],
                    y_length=self._box_records[visual.sequence_number].lengths[1],
                    z_length=self._box_records[visual.sequence_number].lengths[2],
                )
                for visual in visuals
            ]
            # `merge_points=False`: cada caja conserva su propia geometría
            # independiente dentro de la malla combinada -- dos cajas que se
            # tocan cara con cara nunca deben fusionar vértices, para que el
            # resultado visual sea idéntico al de un actor por caja.
            merged = cubes[0] if len(cubes) == 1 else pv.merge(cubes, merge_points=False)
            actor = self._plotter.add_mesh(
                merged,
                color=color_hex,
                opacity=BOX_OPACITY,
                show_edges=True,
                edge_color=ColorRegistry.edge_color(self._theme),
                line_width=BOX_EDGE_LINE_WIDTH,
                name=f"viewer-box-group-{group_index}",
            )
            self._group_actors[key] = actor
            self._actor_group_by_id[id(actor)] = key

            pass  # labels se crean en el bloque vtkTextActor3D más abajo

        dark = self._theme != THEME_LIGHT

        # Un único vtkTextActor3D por SKU en la caja más visible (mayor X + Z).
        # Mantiene el aspecto "impreso en cara" con costo mínimo (N_SKU actores).
        try:
            import vtk as _vtk  # noqa: PLC0415
        except ImportError:
            _vtk = None  # type: ignore[assignment]

        if _vtk is not None:
            seq_to_sku = {v.sequence_number: v.sku for v in scene.placement_visuals}

            # Agrupar boxes por SKU y elegir la más visible (front + top)
            sku_best: dict[str, _BoxRecord] = {}
            for seq_num, rec in self._box_records.items():
                sku = seq_to_sku.get(seq_num, "")
                if not sku:
                    continue
                score = rec.center[0] * 0.6 + rec.center[2] * 0.4  # mayor X y Z
                if sku not in sku_best or score > (
                    sku_best[sku].center[0] * 0.6 + sku_best[sku].center[2] * 0.4
                ):
                    sku_best[sku] = rec

            _FONT = 48
            for sku, rec in sku_best.items():
                cx, cy, cz = rec.center
                dx, dy, dz = rec.lengths

                face_x = cx + dx / 2.0 + 0.15
                face_h, face_w = dz, dy
                rotate_vertical = face_h > face_w * 1.5
                target_dim = face_h if rotate_vertical else face_w
                natural_w_px = _FONT * 0.55 * len(sku)
                scale = target_dim * 0.72 / max(natural_w_px, 1.0)

                try:
                    ta = _vtk.vtkTextActor3D()
                    ta.SetInput(sku)
                    ta.SetPosition(face_x, cy, cz)
                    ta.SetOrientation(0.0, 90.0, 90.0 if rotate_vertical else 0.0)
                    ta.SetScale(scale, scale, 1.0)

                    tp = ta.GetTextProperty()
                    tp.SetFontSize(_FONT)
                    tp.SetBold(True)
                    tp.SetJustificationToCentered()
                    tp.SetVerticalJustificationToCentered()
                    if dark:
                        tp.SetColor(0.94, 0.94, 0.94)
                        tp.SetBackgroundColor(0.10, 0.11, 0.15)
                    else:
                        tp.SetColor(0.04, 0.04, 0.04)
                        tp.SetBackgroundColor(0.98, 0.98, 0.98)
                    tp.SetBackgroundOpacity(0.82)

                    self._plotter.add_actor(ta, reset_camera=False)
                    self._sku_label_actors.setdefault(sku, []).append(ta)
                    self._label_actors.append(ta)
                except Exception:  # noqa: BLE001
                    pass

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
        for actor in self._group_actors.values():
            actor.visibility = visible
        if self._selection_actor is not None:
            self._selection_actor.visibility = visible
        for actor in self._label_actors:
            actor.SetVisibility(1 if visible else 0)
        self._plotter.render()

    def set_axes_visible(self, visible: bool) -> None:
        for actor in self._axes_actors:
            actor.visibility = visible
        self._plotter.render()

    def set_labels_visible(self, visible: bool) -> None:
        for actor in self._label_actors:
            actor.SetVisibility(1 if visible else 0)
        self._plotter.render()

    def set_sku_visible(self, sku: str, visible: bool) -> None:
        """Muestra u oculta las cajas y sus labels para un SKU concreto."""
        for key in self._sku_groups.get(sku, []):
            actor = self._group_actors.get(key)
            if actor is not None:
                actor.visibility = visible
        for label_actor in self._sku_label_actors.get(sku, []):
            label_actor.SetVisibility(1 if visible else 0)
        self._plotter.render()

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------

    def set_selected_placement(self, sequence_number: int | None) -> None:
        """Actualiza la selección visual sin emitir ninguna notificación (uso externo)."""
        self._apply_selection(sequence_number)

    def _apply_selection(self, sequence_number: int | None) -> None:
        """Nunca cambia el color de relleno del grupo compartido -- ver docstring del
        módulo (fase OPT-18). El resalte es un actor de contorno independiente,
        reconstruido aquí (barato: una única caja) y nunca reutilizado entre
        selecciones distintas para no arrastrar tamaño/posición de la caja anterior.
        """
        if self._selection_actor is not None:
            self._plotter.remove_actor(self._selection_actor, render=False)
            self._selection_actor = None

        self._selected_sequence_number = sequence_number

        if sequence_number is not None:
            record = self._box_records.get(sequence_number)
            if record is not None:
                highlight = pv.Cube(
                    center=record.center,
                    x_length=record.lengths[0],
                    y_length=record.lengths[1],
                    z_length=record.lengths[2],
                )
                self._selection_actor = self._plotter.add_mesh(
                    highlight,
                    style="wireframe",
                    color=ColorRegistry.selection_color(self._theme),
                    line_width=SELECTION_LINE_WIDTH,
                    name="viewer-selection-highlight",
                    pickable=False,
                )

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
        sequence_number = None
        if actor is not None:
            group_key = self._actor_group_by_id.get(id(actor))
            if group_key is not None:
                point = getattr(self._plotter, "picked_point", None)
                sequence_number = self._nearest_box_in_group(group_key, point)
        self._apply_selection(sequence_number)
        if self._on_selection_changed is not None:
            self._on_selection_changed(sequence_number)

    def _nearest_box_in_group(
        self, group_key: _GroupKey, point: tuple[float, float, float] | None
    ) -> int | None:
        """Resuelve qué caja concreta de un grupo (varias comparten un mismo actor de
        malla combinada) corresponde a un punto de click en coordenadas del mundo.

        Nunca depende de índices de celda/punto de VTK (la malla combinada no
        garantiza un orden estable útil para eso): compara `point` contra el
        centro ya conocido de cada caja del grupo (`_box_records`) y devuelve la
        más cercana. Sin `point` (p. ej. un picker que no lo proporcione), se
        devuelve la primera caja del grupo en vez de no seleccionar nada.
        """
        members = self._group_members.get(group_key, [])
        if not members:
            return None
        if point is None:
            return members[0]
        px, py, pz = point

        def _squared_distance(sequence_number: int) -> float:
            cx, cy, cz = self._box_records[sequence_number].center
            return (cx - px) ** 2 + (cy - py) ** 2 + (cz - pz) ** 2

        return min(members, key=_squared_distance)

    def find_placement_actor(self, sequence_number: int) -> Any | None:
        """El actor de malla combinada que renderiza esta caja (compartido con
        cualquier otra caja del mismo grupo visual -- fase OPT-18)."""
        record = self._box_records.get(sequence_number)
        if record is None:
            return None
        return self._group_actors.get(record.group_key)

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
        """Encuadra la cámara sobre una única caja. No hace nada si no existe.

        Calcula los límites directamente desde `_BoxRecord` (centro +
        longitudes), no desde `actor.GetBounds()`: desde la fase OPT-18 el actor
        es una malla combinada compartida por todo el grupo visual, y sus
        límites abarcarían todas las cajas del grupo, no solo esta.
        """
        record = self._box_records.get(sequence_number)
        if record is None:
            return
        cx, cy, cz = record.center
        half_x, half_y, half_z = (length / 2.0 for length in record.lengths)
        bounds = (cx - half_x, cx + half_x, cy - half_y, cy + half_y, cz - half_z, cz + half_z)
        self._plotter.reset_camera(bounds=bounds)
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
