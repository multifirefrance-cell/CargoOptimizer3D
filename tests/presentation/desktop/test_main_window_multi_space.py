"""Pruebas de integración: `MainWindow` y la optimización multi-espacio (OPT-01, UI).

Mismo patrón de espera/mensajes que `test_main_window_optimization.py`
(el archivo equivalente para la optimización de un solo espacio):
`QMessageBox.warning/.critical/.information` son modales y se cuelgan
bajo la plataforma Qt `offscreen` si no se sustituyen por `monkeypatch`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QListWidgetItem, QMessageBox

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.models import MultiSpaceAssignmentResult
from cargo_optimizer.application.multi_space_assignment import MultiSpaceAssignmentEngine
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.presentation.desktop.dialogs.multi_space_setup_dialog import (
    MultiSpaceSetupDialog,
)
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import AppSettings
from cargo_optimizer.presentation.desktop.workers.multi_space_optimization_worker import (
    MultiSpaceOptimizationWorker,
)

_SMALL_SPACE = LoadingSpace(
    name="Furgón pequeño de pruebas",
    category=LoadingSpaceCategory.VAN,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
)


def _cube_unit(quantity: int) -> LoadUnit:
    # Un cubo de 60 cm no cabe dos veces en un espacio de 100x100x100
    # (ver tests/application/_helpers.py): garantiza, de forma
    # determinista, que hacen falta tantos espacios como `quantity`.
    return LoadUnit(
        sku="CUBE",
        name="Cubo de pruebas",
        dimensions=Dimensions3D(60.0, 60.0, 60.0),
        weight_kg=5.0,
        quantity=quantity,
    )


def _wait_until_multi_space_worker_finishes(
    app: QApplication, window: MainWindow, timeout_s: float = 15.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while window._multi_space_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._multi_space_worker is None, "El worker no terminó dentro del tiempo esperado"


def _silence_message_box(monkeypatch: pytest.MonkeyPatch, method: str) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        calls.append(args)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, method, staticmethod(_fake))
    return calls


def _allow_close_without_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
    )


def _fake_setup_dialog_selecting_current_space(
    monkeypatch: pytest.MonkeyPatch, *, max_spaces: int | None = None
) -> None:
    """Simula que el usuario elige "espacio actual" en `MultiSpaceSetupDialog` y acepta."""

    def _exec(self: MultiSpaceSetupDialog) -> int:
        assert self._available_list.count() >= 1
        first_item = self._available_list.item(0)
        space = first_item.data(Qt.ItemDataRole.UserRole)
        moved = QListWidgetItem(first_item.text())
        moved.setData(Qt.ItemDataRole.UserRole, space)
        self._selected_list.addItem(moved)
        if max_spaces is not None:
            self._limit_check.setChecked(True)
            self._max_spaces_spin.setValue(max_spaces)
        self._on_accept()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(MultiSpaceSetupDialog, "exec", _exec)


def _fake_setup_dialog_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MultiSpaceSetupDialog, "exec", lambda self: QDialog.DialogCode.Rejected)


def test_multi_space_no_candidates_shows_warning(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings = _silence_message_box(monkeypatch, "warning")
    window = MainWindow(app_settings, catalog_service=None)
    window.loading_space_form_panel._name_edit.setText("   ")  # espacio actual inválido

    window.action_run_multi_space_optimization.trigger()

    assert window._multi_space_worker is None
    assert len(warnings) == 1
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_multi_space_setup_dialog_cancelled_does_not_run(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_setup_dialog_rejected(monkeypatch)
    window = MainWindow(app_settings, catalog_service=None)

    window.action_run_multi_space_optimization.trigger()

    assert window._multi_space_worker is None
    window.close()


def test_multi_space_no_products_shows_warning(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_setup_dialog_selecting_current_space(monkeypatch)
    warnings = _silence_message_box(monkeypatch, "warning")
    window = MainWindow(app_settings, catalog_service=None)

    window.action_run_multi_space_optimization.trigger()

    assert window._multi_space_worker is None
    assert len(warnings) == 1
    window.close()


def test_request_built_from_ui_uses_current_space_and_products(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_setup_dialog_selecting_current_space(monkeypatch, max_spaces=7)
    window = MainWindow(app_settings, catalog_service=None)
    for _ in range(3):
        window.product_table_panel.model.add_default_product()
    expected_space = window.loading_space_form_panel.build_loading_space()

    window.action_run_multi_space_optimization.trigger()

    assert window._multi_space_worker is not None
    request = window._multi_space_worker._request
    assert len(request.loading_space_candidates) == 1
    actual_space = request.loading_space_candidates[0]
    # `build_loading_space()` genera un `id` nuevo en cada llamada
    # (`field(default_factory=uuid4)`): comparamos el contenido real,
    # no la identidad de un `LoadingSpace` construido por separado.
    assert actual_space.name == expected_space.name
    assert actual_space.category == expected_space.category
    assert actual_space.internal_dimensions == expected_space.internal_dimensions
    assert len(request.load_units) == 3
    assert request.max_spaces == 7

    _wait_until_multi_space_worker_finishes(qapp, window)
    assert window._last_multi_space_result is not None
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_multi_space_run_populates_global_summary_and_needs_multiple_spaces(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_setup_dialog_selecting_current_space(monkeypatch)
    window = MainWindow(app_settings, catalog_service=None)
    window.loading_space_form_panel.set_current_profile_name("Personalizado")
    window.loading_space_form_panel._name_edit.setText(_SMALL_SPACE.name)
    window.loading_space_form_panel._length_spin.setValue(100.0)
    window.loading_space_form_panel._width_spin.setValue(100.0)
    window.loading_space_form_panel._height_spin.setValue(100.0)
    window.product_table_panel.model.add_units([_cube_unit(quantity=3)])

    window.action_run_multi_space_optimization.trigger()
    _wait_until_multi_space_worker_finishes(qapp, window)

    result = window._last_multi_space_result
    assert result is not None
    assert result.spaces_used_count == 3
    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert window.multi_space_results_panel._spaces_used_label.text() == "3"
    assert window.multi_space_results_panel._requested_label.text() == "3"
    assert window.multi_space_results_panel._packed_label.text() == "3"
    assert window.multi_space_results_panel._pending_label.text() == "0"
    assert window.results_tabs.currentWidget() is window.multi_space_results_panel
    _allow_close_without_saving(monkeypatch)
    window.close()


def _real_two_space_result() -> tuple[MultiSpaceAssignmentResult, dict]:
    request_units = (_cube_unit(quantity=2),)
    from cargo_optimizer.application.models import MultiSpaceAssignmentRequest

    request = MultiSpaceAssignmentRequest(
        loading_space_candidates=(_SMALL_SPACE,), load_units=request_units
    )
    result = MultiSpaceAssignmentEngine().assign(request)
    load_units_by_id = {unit.id: unit for unit in request_units}
    return result, load_units_by_id


def test_multi_space_space_selected_updates_viewer(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    result, load_units_by_id = _real_two_space_result()
    assert result.spaces_used_count == 2

    calls: list[Any] = []
    monkeypatch_display = window.viewer_widget.display_result

    def _recording_display_result(displayed_result: object, units: object) -> None:
        calls.append(displayed_result)
        monkeypatch_display(displayed_result, units)  # type: ignore[arg-type]

    window.viewer_widget.display_result = _recording_display_result  # type: ignore[method-assign]

    window._on_multi_space_finished(result)
    assert calls == [result.space_results[0]]

    window.multi_space_results_panel._space_combo.setCurrentIndex(1)
    assert calls[-1] is result.space_results[1]

    window.close()


def test_multi_space_engine_error_shows_critical_message(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_setup_dialog_selecting_current_space(monkeypatch)
    errors = _silence_message_box(monkeypatch, "critical")

    def _fake_start(self: MultiSpaceOptimizationWorker) -> None:
        self.optimization_failed.emit("fallo simulado del motor multi-espacio")
        self.finished.emit()

    monkeypatch.setattr(MultiSpaceOptimizationWorker, "start", _fake_start)

    window = MainWindow(app_settings, catalog_service=None)
    window.product_table_panel.model.add_default_product()

    window.action_run_multi_space_optimization.trigger()

    assert len(errors) == 1
    assert window._state_status_label.text() == "Estado: error"
    assert "fallo simulado" in window.log_panel.text()
    window.close()


def test_cancel_multi_space_dispatches_to_worker_token(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings, catalog_service=None)

    class _FakeRunningWorker:
        def __init__(self) -> None:
            self.cancellation_token = CancellationToken()

        def isRunning(self) -> bool:  # noqa: N802 (nombre impuesto por QThread)
            return True

    fake_worker = _FakeRunningWorker()
    window._multi_space_worker = fake_worker  # type: ignore[assignment]

    window._on_cancel_optimization()

    assert fake_worker.cancellation_token.is_cancelled()
    assert window._cancel_requested is True

    # El doble de prueba no implementa el resto de la API de QThread
    # (`.wait()`, etc.): se limpia antes de cerrar la ventana para no
    # confundir esta prueba de despacho de cancelación con el ciclo de
    # vida real de un worker, que ya cubren las pruebas del propio
    # worker y `closeEvent`.
    window._multi_space_worker = None
    window.close()


def test_running_normal_optimization_clears_stale_multi_space_result(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regresión: un resultado multi-espacio previo no debe sobrevivir a una optimización normal.

    Antes de esta corrección, `_last_multi_space_result` y la pestaña
    "Multi-espacio" seguían mostrando datos de una ejecución anterior
    tras correr la optimización normal — el selector de espacio podía
    entonces sobrescribir en silencio el visor recién actualizado.
    """
    window = MainWindow(app_settings, catalog_service=None)
    result, load_units_by_id = _real_two_space_result()
    window._on_multi_space_finished(result)
    assert window._last_multi_space_result is not None

    for _ in range(3):
        window.product_table_panel.model.add_default_product()
    window.action_run_optimization.trigger()

    assert window._last_multi_space_result is None
    assert window.multi_space_results_panel._spaces_used_label.text() == "—"

    _allow_close_without_saving(monkeypatch)
    window.close()


def test_close_event_waits_for_running_multi_space_worker(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    """Regresión: `closeEvent` solo esperaba `_optimization_worker`, nunca el multi-espacio.

    Cerrar la ventana durante una optimización multi-espacio en curso
    podía destruir los widgets mientras el `QThread` seguía corriendo y
    más tarde intentaba emitir señales hacia objetos Qt ya liberados.
    """
    window = MainWindow(app_settings, catalog_service=None)

    class _FakeWorker:
        def __init__(self) -> None:
            self.cancellation_token = CancellationToken()
            self.wait_called_with: int | None = None

        def isRunning(self) -> bool:  # noqa: N802
            return True

        def wait(self, timeout_ms: int) -> bool:
            self.wait_called_with = timeout_ms
            return True

    fake_worker = _FakeWorker()
    window._multi_space_worker = fake_worker  # type: ignore[assignment]

    window.close()

    assert fake_worker.cancellation_token.is_cancelled()
    assert fake_worker.wait_called_with == 5000


def test_save_project_shows_multi_space_not_saved_warning(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    infos: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: infos.append(a) or QMessageBox.StandardButton.Ok),
    )
    out_path = tmp_path / "proyecto.cargo3d"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out_path), ""))
    )

    window = MainWindow(app_settings, catalog_service=None)
    result, _load_units_by_id = _real_two_space_result()
    window._last_multi_space_result = result

    saved = window._on_save_project_as()

    assert saved is True
    assert out_path.exists()
    assert len(infos) == 1
    assert "Los resultados multi-espacio todavía no se guardan" in infos[0][-1]
    window.close()
