"""Pruebas de `Packing3DViewer` bajo la plataforma Qt `offscreen`.

Bajo `offscreen` (la que usa toda esta suite), `Packing3DViewer` entra
**siempre**, de forma determinista, en modo de repuesto —
`_try_create_interactor` lo detecta explícitamente antes de intentar
construir un `QtInteractor` real (ver `widget.py` y
`docs/ThreeDViewer.md`). Esto no es una limitación de las pruebas: es
precisamente el comportamiento de seguridad que se está probando. El
renderizado real (`QtInteractor` sobre una plataforma nativa) se probó
manualmente fuera de la plataforma "offscreen" — ver el informe de la
fase 6.1 — y `test_scene_controller.py` cubre la lógica real de
construcción de escena contra VTK de verdad (con un
`pv.Plotter(off_screen=True)`, que sí es seguro bajo esta plataforma).
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.presentation.desktop.viewer.widget import Packing3DViewer


def _empty_result() -> PackingResult:
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    )
    return PackingResult(
        loading_space=space,
        placements=(),
        unpacked_units=(),
        requested_count=0,
        packed_count=0,
        used_volume_cm3=0.0,
        used_weight_kg=0.0,
        execution_time_seconds=0.0,
        algorithm_name="greedy_extreme_point_v1",
    )


def test_viewer_falls_back_under_offscreen_platform(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    assert viewer.is_available() is False
    assert viewer.unavailable_reason() is not None
    assert "offscreen" in viewer.unavailable_reason()


def test_fallback_widget_is_shown(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    fallback = viewer.findChild(QWidget, "packing3DViewerFallback")
    assert fallback is not None


def test_all_public_methods_are_safe_no_ops_when_unavailable(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    viewer.display_result(_empty_result(), {})
    viewer.clear_scene()
    viewer.reset_camera()
    viewer.set_container_visible(True)
    viewer.set_boxes_visible(False)
    viewer.set_axes_visible(True)
    viewer.set_selected_placement(None)
    viewer.set_selected_placement(1)
    viewer.focus_placement(1)
    viewer.set_dark_theme(True)
    viewer.set_dark_theme(False)
    assert viewer.find_placement_visual(1) is None
    viewer.shutdown()
    # Ninguna llamada anterior debe haber lanzado una excepción.


def test_placement_selected_signal_exists_and_can_be_emitted(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    received: list[object] = []
    viewer.placement_selected.connect(received.append)

    viewer.placement_selected.emit(5)
    viewer.placement_selected.emit(None)

    assert received == [5, None]


def test_shutdown_is_idempotent(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    viewer.shutdown()
    viewer.shutdown()  # no debe lanzar excepción la segunda vez


def test_viewer_has_expanding_size_policy(qapp: QApplication) -> None:
    viewer = Packing3DViewer()
    assert viewer.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    assert viewer.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding
