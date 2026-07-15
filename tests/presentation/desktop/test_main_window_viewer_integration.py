"""Pruebas de integración: `MainWindow` y el visor 3D (fase 6.1).

Bajo la plataforma Qt `offscreen`, `Packing3DViewer` está siempre en
modo de repuesto (ver `test_packing_3d_viewer_widget.py`), así que
estas pruebas no verifican renderizado real — verifican que
`MainWindow` **orquesta correctamente** el visor y el panel de
detalles (qué se llama, cuándo, con qué datos), que es justo la parte
de la fase 6.1 que vive en `MainWindow` y que sí puede probarse sin
GPU. El propio `Packing3DViewer` siendo no-op seguro en modo de
repuesto es lo que permite que estas pruebas funcionen sin ninguna
condición especial.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import pytest
from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import AppSettings
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel


def _wait_until_worker_finishes(
    app: QApplication, window: MainWindow, timeout_s: float = 15.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while window._optimization_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._optimization_worker is None, "El worker no terminó dentro del tiempo esperado"


def test_main_window_creates_viewer_and_details_dock(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.viewer_widget is not None
    assert window.selection_details_panel is not None
    assert window.selection_details_dock.widget() is window.selection_details_panel
    window.close()


def test_view_menu_actions_exist_and_are_wired(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.action_reset_camera.isEnabled()
    assert window.action_toggle_container_visible.isCheckable()
    assert window.action_toggle_container_visible.isChecked()
    assert window.action_toggle_boxes_visible.isCheckable()
    assert window.action_toggle_axes_visible.isCheckable()
    assert window.action_toggle_selection_details_dock.isCheckable()
    window.close()


def test_reset_camera_action_calls_viewer(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    calls: list[str] = []
    monkeypatch.setattr(window.viewer_widget, "reset_camera", lambda: calls.append("reset"))

    window.action_reset_camera.trigger()

    assert calls == ["reset"]
    window.close()


def test_visibility_actions_call_viewer_setters(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    container_calls: list[bool] = []
    boxes_calls: list[bool] = []
    axes_calls: list[bool] = []
    monkeypatch.setattr(window.viewer_widget, "set_container_visible", container_calls.append)
    monkeypatch.setattr(window.viewer_widget, "set_boxes_visible", boxes_calls.append)
    monkeypatch.setattr(window.viewer_widget, "set_axes_visible", axes_calls.append)

    window.action_toggle_container_visible.trigger()
    window.action_toggle_boxes_visible.trigger()
    window.action_toggle_axes_visible.trigger()

    assert container_calls == [False]  # empieza marcada (True) -> al pulsar pasa a False
    assert boxes_calls == [False]
    assert axes_calls == [False]
    window.close()


def test_run_optimization_clears_viewer_and_details_panel(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    for _ in range(3):
        window.product_table_panel.model.add_default_product()

    clear_calls: list[str] = []
    monkeypatch.setattr(window.viewer_widget, "clear_scene", lambda: clear_calls.append("scene"))
    monkeypatch.setattr(
        window.selection_details_panel, "clear", lambda: clear_calls.append("details")
    )

    window.action_run_optimization.trigger()

    assert "scene" in clear_calls
    assert "details" in clear_calls
    _wait_until_worker_finishes(qapp, window)
    window.close()


def test_optimization_finished_displays_result_in_viewer(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    for _ in range(3):
        window.product_table_panel.model.add_default_product()

    received: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        window.viewer_widget,
        "display_result",
        lambda result, load_units_by_id: received.append((result, load_units_by_id)),
    )

    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)

    assert len(received) == 1
    result, load_units_by_id = received[0]
    assert result.packed_count == 3
    assert set(load_units_by_id.keys()) == {
        unit.id for unit in window.product_table_panel.model.load_units()
    }
    window.close()


def test_placement_selected_signal_updates_details_panel(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    visual = PlacementVisualModel(
        sequence_number=1,
        instance_number=1,
        load_unit_id=UUID(int=0),
        sku="BOX-1",
        name="Caja",
        position=(0.0, 0.0, 0.0),
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
    monkeypatch.setattr(window.viewer_widget, "find_placement_visual", lambda seq: visual)

    window._on_placement_selected(1)
    assert window.selection_details_panel._sku_label.text() == "BOX-1"

    window._on_placement_selected(None)
    assert window.selection_details_panel._sku_label.text() == "—"
    window.close()


def test_placement_selected_with_unknown_sequence_clears_panel(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    monkeypatch.setattr(window.viewer_widget, "find_placement_visual", lambda seq: None)

    window._on_placement_selected(999)

    assert window.selection_details_panel._sku_label.text() == "—"
    window.close()


def test_new_project_clears_viewer_and_details(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    clear_calls: list[str] = []
    monkeypatch.setattr(window.viewer_widget, "clear_scene", lambda: clear_calls.append("scene"))
    monkeypatch.setattr(
        window.selection_details_panel, "clear", lambda: clear_calls.append("details")
    )

    window.action_new.trigger()

    assert "scene" in clear_calls
    assert "details" in clear_calls
    window.close()


def test_close_event_shuts_down_viewer(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    calls: list[str] = []
    monkeypatch.setattr(window.viewer_widget, "shutdown", lambda: calls.append("shutdown"))

    window.close()

    assert calls == ["shutdown"]


def test_theme_toggle_updates_viewer_theme(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    calls: list[bool] = []
    monkeypatch.setattr(window.viewer_widget, "set_dark_theme", calls.append)

    window.action_dark_theme.trigger()
    window.action_light_theme.trigger()

    assert calls == [True, False]
    window.close()
