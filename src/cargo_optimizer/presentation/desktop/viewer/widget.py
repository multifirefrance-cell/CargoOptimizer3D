"""`Packing3DViewer`: widget público del visor 3D.

Único contrato que el resto de la aplicación conoce (ver ADR-0011):
recibe un `PackingResult` ya calculado (`display_result`), nunca
ejecuta `PackingEngine` ni ninguna pieza de `cargo_optimizer.optimization`.

Si PyVista/PyVistaQt no están disponibles, o el contexto OpenGL no se
puede inicializar, el widget se degrada a un contenido de repuesto
informativo (`is_available() == False`) y todos sus métodos públicos
pasan a ser no-op seguros — `MainWindow` nunca necesita comprobar
`is_available()` antes de llamarlos.

**Hallazgo real durante la implementación** (documentado también en
`docs/ThreeDViewer.md`): bajo la plataforma Qt `offscreen` (la que usa
la suite de pruebas, `QT_QPA_PLATFORM=offscreen`), `pyvistaqt.QtInteractor`
no falla con una excepción Python — provoca un **segmentation fault**
nativo en Windows (`vtkWin32OpenGLRenderWindow: failed to get valid
pixel format`), porque VTK necesita una ventana nativa real para
embeber su contexto OpenGL y la plataforma "offscreen" de Qt
deliberadamente no crea ninguna. Un `try/except` no habría evitado ese
crash (no es una excepción Python). Por eso este widget comprueba
`QApplication.platformName() == "offscreen"` **antes** de intentar
construir un `QtInteractor`, y trata ese caso como "3D no disponible"
de forma proactiva, no reactiva. En producción (plataforma nativa de
Qt, con una ventana real) este caso nunca se activa.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QVBoxLayout, QWidget

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.presentation.desktop.viewer.constants import THEME_DARK, THEME_LIGHT
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel
from cargo_optimizer.presentation.desktop.viewer.scene_builder import SceneBuilder
from cargo_optimizer.presentation.desktop.viewer.scene_controller import SceneController

_FALLBACK_TITLE = "Vista 3D no disponible"


class Packing3DViewer(QWidget):
    """Visor 3D interactivo de un `PackingResult`, con degradación segura si el 3D no arranca."""

    placement_selected = Signal(object)  # int | None — PySide6 no admite Signal(int | None)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("packing3DViewer")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._controller: SceneController | None = None
        self._unavailable_reason: str | None = None
        self._theme = THEME_LIGHT

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        interactor = self._try_create_interactor()
        if interactor is None:
            layout.addWidget(self._build_fallback_widget())
            return

        self._controller = SceneController(interactor, self._theme)
        self._controller.set_selection_changed_callback(self._on_selection_changed)
        layout.addWidget(interactor)

    # ------------------------------------------------------------------
    # Inicialización / fallback
    # ------------------------------------------------------------------

    def _try_create_interactor(self) -> Any:
        """Devuelve un `QtInteractor` (QWidget + API de `pyvista.Plotter`) o `None`.

        Tipado como `Any`, justificado: `pyvistaqt` no distribuye stubs
        de tipos completos, y `QtInteractor` necesita satisfacer a la vez
        `QWidget` (para añadirlo al layout) y `PyVistaPlotterLike` (para
        `SceneController`) — dos protocolos que mypy no puede verificar
        estructuralmente sobre una clase de una biblioteca externa sin
        stubs. `SceneController` sigue tipando su propio parámetro como
        `PyVistaPlotterLike`, así que la superficie sin verificar queda
        contenida aquí, no se propaga.
        """
        app = QApplication.instance()
        if isinstance(app, QApplication) and app.platformName() == "offscreen":
            self._unavailable_reason = (
                "La plataforma Qt activa es 'offscreen': VTK no puede crear una "
                "ventana nativa para el renderizado 3D en este entorno."
            )
            return None

        try:
            from pyvistaqt import QtInteractor
        except ImportError as exc:
            self._unavailable_reason = f"PyVista/PyVistaQt no está instalado: {exc}"
            return None

        try:
            return QtInteractor(self)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - cualquier fallo de VTK/OpenGL debe degradar, no propagar
            self._unavailable_reason = f"No se pudo inicializar el motor de render 3D: {exc}"
            return None

    def _build_fallback_widget(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("packing3DViewerFallback")

        icon_label = QLabel("⚠", container)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_font = icon_label.font()
        icon_font.setPointSize(icon_font.pointSize() + 24)
        icon_label.setFont(icon_font)

        title_label = QLabel(_FALLBACK_TITLE, container)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)

        reason_label = QLabel(self._unavailable_reason or "Motivo desconocido.", container)
        reason_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reason_label.setWordWrap(True)
        reason_font = reason_label.font()
        reason_font.setItalic(True)
        reason_label.setFont(reason_font)

        for label in (icon_label, title_label, reason_label):
            label.setEnabled(False)

        layout = QVBoxLayout(container)
        layout.addStretch(1)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(reason_label)
        layout.addStretch(1)
        return container

    def is_available(self) -> bool:
        """`False` si el visor está en modo de repuesto (sin renderizado 3D real)."""
        return self._controller is not None

    def unavailable_reason(self) -> str | None:
        """El motivo técnico del modo de repuesto, o `None` si el visor sí está disponible."""
        return self._unavailable_reason

    def _on_selection_changed(self, sequence_number: int | None) -> None:
        self.placement_selected.emit(sequence_number)

    # ------------------------------------------------------------------
    # API pública — todos no-op seguros si is_available() es False
    # ------------------------------------------------------------------

    def display_result(
        self, result: PackingResult, load_units_by_id: Mapping[UUID, LoadUnit]
    ) -> None:
        if self._controller is None:
            return
        scene = SceneBuilder().build(result, load_units_by_id)
        self._controller.load_scene(scene)

    def clear_scene(self) -> None:
        if self._controller is not None:
            self._controller.clear_scene()

    def reset_camera(self) -> None:
        if self._controller is not None:
            self._controller.reset_camera()

    def set_container_visible(self, visible: bool) -> None:
        if self._controller is not None:
            self._controller.set_container_visible(visible)

    def set_boxes_visible(self, visible: bool) -> None:
        if self._controller is not None:
            self._controller.set_boxes_visible(visible)

    def set_axes_visible(self, visible: bool) -> None:
        if self._controller is not None:
            self._controller.set_axes_visible(visible)

    def set_selected_placement(self, sequence_number: int | None) -> None:
        """Actualiza la selección sin emitir `placement_selected` (uso externo, p. ej. tabla)."""
        if self._controller is not None:
            self._controller.set_selected_placement(sequence_number)

    def focus_placement(self, sequence_number: int) -> None:
        if self._controller is not None:
            self._controller.focus_placement(sequence_number)

    def find_placement_visual(self, sequence_number: int) -> PlacementVisualModel | None:
        """El modelo visual de la escena actual con ese `sequence_number`, si existe."""
        if self._controller is None:
            return None
        return self._controller.find_placement_visual(sequence_number)

    def set_dark_theme(self, enabled: bool) -> None:
        self._theme = THEME_DARK if enabled else THEME_LIGHT
        if self._controller is not None:
            self._controller.apply_theme(self._theme)

    def export_screenshot_png(self) -> bytes | None:
        """PNG en memoria de la vista 3D actual, o `None` si el visor no está disponible.

        Uso previsto: `infrastructure/pdf` (fase 9.1) recibe estos bytes
        ya capturados desde `MainWindow` — el visor nunca sabe nada de
        PDF ni de `reportlab`, mismo desacoplo que ya protege a
        `viewer/` frente a `optimization` (ADR-0011).
        """
        if self._controller is None:
            return None
        return self._controller.export_screenshot_png()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Libera el `Plotter`/`QtInteractor`. Debe llamarse explícitamente al cerrar la ventana.

        No se apoya en `closeEvent`: este widget es un hijo embebido en
        un layout, no una ventana de nivel superior, así que Qt nunca le
        entrega un `closeEvent` propio cuando `MainWindow` se cierra —
        `MainWindow.closeEvent` debe llamar a este método explícitamente
        (igual que ya cancela un `OptimizationWorker` en curso, fase 5.1).
        """
        if self._controller is not None:
            self._controller.close()
            self._controller = None
