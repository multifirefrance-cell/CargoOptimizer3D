"""Pruebas de integración: `MainWindow` ejecutando `PackingEngine` de verdad.

`QMessageBox.warning`/`.critical` son modales: en un entorno sin
usuario (como esta suite, con la plataforma Qt `offscreen`) se quedan
esperando un clic que nunca llega y la prueba se cuelga. Cada prueba
que puede disparar uno los sustituye por `monkeypatch` con una función
que solo registra la llamada y devuelve inmediatamente.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import PROFILE_CUSTOM
from cargo_optimizer.presentation.desktop.settings import AppSettings

_SPACE = LoadingSpace(
    name="Espacio de prueba",
    category=LoadingSpaceCategory.OTHER,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
)


def _result_with_pending(*, pending_count: int, packed_count: int = 1) -> PackingResult:
    """Un `PackingResult` real con `pending_count` unidades pendientes de un único SKU."""
    unit = LoadUnit(
        sku="PEND-SKU", name="Pendiente", dimensions=Dimensions3D(10, 10, 10), weight_kg=5.0
    )
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.LWH_XYZ)
    placements = tuple(
        Placement(unit.id, i, Position3D(0, 0, 0), orientation, i)
        for i in range(1, packed_count + 1)
    )
    unpacked = tuple(
        UnpackedUnit(unit.id, packed_count + i, "no_feasible_position", "sin espacio")
        for i in range(1, pending_count + 1)
    )
    return PackingResult(
        loading_space=_SPACE,
        placements=placements,
        unpacked_units=unpacked,
        requested_count=packed_count + pending_count,
        packed_count=packed_count,
        used_volume_cm3=1000.0,
        used_weight_kg=10.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
    )


def _wait_until_worker_finishes(
    app: QApplication, window: MainWindow, timeout_s: float = 15.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while window._optimization_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._optimization_worker is None, "El worker no terminó dentro del tiempo esperado"


def _silence_message_box(monkeypatch: pytest.MonkeyPatch, method: str) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        calls.append(args)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, method, staticmethod(_fake))
    return calls


def _allow_close_without_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita que `window.close()` se cuelgue esperando un `QMessageBox.question` real.

    Desde la fase 7.0, `MainWindow` pregunta antes de cerrar si hay
    cambios sin guardar (ver `_confirm_discard_unsaved_changes`). Las
    pruebas de esta suite no guardan a propósito (no es lo que están
    probando), así que responden "Descartar" para poder cerrar la
    ventana sin bloquear la suite bajo la plataforma `offscreen`.
    """

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))


def test_run_optimization_without_products_shows_warning_and_does_not_run(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings = _silence_message_box(monkeypatch, "warning")
    window = MainWindow(app_settings)

    window.action_run_optimization.trigger()

    assert window._optimization_worker is None
    assert len(warnings) == 1
    window.close()


def test_run_optimization_with_invalid_custom_space_shows_warning(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings = _silence_message_box(monkeypatch, "warning")
    window = MainWindow(app_settings)
    window.loading_space_form_panel.set_current_profile_name(PROFILE_CUSTOM)
    window.loading_space_form_panel._name_edit.setText("   ")

    window.action_run_optimization.trigger()

    assert window._optimization_worker is None
    assert len(warnings) == 1
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_run_optimization_executes_and_populates_results(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    for _ in range(5):
        window.product_table_panel.model.add_default_product()

    window.action_run_optimization.trigger()
    assert window._optimization_worker is not None
    assert not window.action_run_optimization.isEnabled()
    assert not window.product_table_panel.isEnabled()
    assert not window.loading_space_form_panel.isEnabled()
    assert window.action_cancel_optimization.isEnabled()

    _wait_until_worker_finishes(qapp, window)

    assert window.results_panel._requested_label.text() == "5"
    assert window.results_panel._packed_label.text() == "5"
    assert window.results_panel._pending_label.text() == "0"
    assert window.action_run_optimization.isEnabled()
    assert window.product_table_panel.isEnabled()
    assert window.loading_space_form_panel.isEnabled()
    assert not window.action_cancel_optimization.isEnabled()
    assert not window._progress_bar.isVisible()
    # El estado de "finalizado" lo cuenta únicamente `results_panel` (fase
    # de mejoras UX, Parte 6): la barra de estado vuelve a "listo" en vez
    # de duplicar la misma información.
    assert window.results_panel._status_label.text() == "Finalizado"
    assert window._state_status_label.text() == "Estado: listo"
    assert "finalizada" in window.log_panel.text().lower()
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_optimization_run_does_not_change_splitter_or_viewer_structure(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Secciones 1-2: iniciar/terminar una optimización real no debe alterar
    # la estructura del splitter visor/resultados ni encoger el visor --
    # solo cambian estado/progreso/KPIs, nunca la distribución general.
    window = MainWindow(app_settings)
    window.resize(1280, 900)
    window.show()
    for _ in range(5):
        window.product_table_panel.model.add_default_product()
    qapp.processEvents()

    sizes_before = list(window.viewer_results_splitter.sizes())
    viewer_min_height_before = window.viewer_widget.minimumHeight()

    window.action_run_optimization.trigger()
    qapp.processEvents()
    sizes_during = list(window.viewer_results_splitter.sizes())
    assert window.viewer_results_splitter.widget(0) is window.viewer_widget
    assert window.viewer_results_splitter.widget(1) is window.results_tabs

    _wait_until_worker_finishes(qapp, window)
    qapp.processEvents()
    sizes_after = list(window.viewer_results_splitter.sizes())

    assert sizes_during == sizes_before
    assert sizes_after == sizes_before
    assert window.viewer_widget.minimumHeight() == viewer_min_height_before
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_cancel_optimization_leaves_interface_consistent(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    for _ in range(80):
        window.product_table_panel.model.add_default_product()

    window.action_run_optimization.trigger()
    assert window._optimization_worker is not None

    window.action_cancel_optimization.trigger()
    assert window._cancel_requested is True
    assert not window.action_cancel_optimization.isEnabled()

    _wait_until_worker_finishes(qapp, window)

    assert window.action_run_optimization.isEnabled()
    assert not window.action_cancel_optimization.isEnabled()
    assert window.product_table_panel.isEnabled()
    assert window.loading_space_form_panel.isEnabled()
    assert not window._progress_bar.isVisible()
    assert "cancelaci" in window.log_panel.text().lower()
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_cancel_optimization_without_running_worker_is_a_no_op(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window.action_cancel_optimization.trigger()  # no debe lanzar excepción
    assert window._optimization_worker is None
    window.close()


def test_optimization_failed_shows_critical_message_and_logs(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors = _silence_message_box(monkeypatch, "critical")
    window = MainWindow(app_settings)

    window._on_optimization_failed("fallo simulado")

    assert len(errors) == 1
    assert window._state_status_label.text() == "Estado: error"
    assert "fallo simulado" in window.log_panel.text()
    window.close()


def test_unpacked_units_and_pending_count_populate_when_space_is_too_small(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    window.loading_space_form_panel.set_current_profile_name(PROFILE_CUSTOM)
    window.loading_space_form_panel._name_edit.setText("Caja diminuta")
    window.loading_space_form_panel._length_spin.setValue(40.0)
    window.loading_space_form_panel._width_spin.setValue(30.0)
    window.loading_space_form_panel._height_spin.setValue(20.0)
    for _ in range(3):
        window.product_table_panel.model.add_default_product()

    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)

    assert window.results_panel._pending_label.text() != "0"
    assert window.unpacked_table_panel.model.rowCount() > 0
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_populate_results_updates_warnings_panel_and_summary(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    from cargo_optimizer.domain.dimensions import Dimensions3D
    from cargo_optimizer.domain.enums import LoadingSpaceCategory
    from cargo_optimizer.domain.loading_space import LoadingSpace
    from cargo_optimizer.domain.packing_result import PackingResult

    window = MainWindow(app_settings)
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    )
    result = PackingResult(
        loading_space=space,
        placements=(),
        unpacked_units=(),
        requested_count=0,
        packed_count=0,
        used_volume_cm3=0.0,
        used_weight_kg=0.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
        warnings=("Aviso de prueba A", "Aviso de prueba B"),
    )

    window._populate_results(result)

    assert window.results_panel._warnings_label.text() == "2"
    window.close()


def test_populate_results_fills_pending_sku_breakdown_matching_total(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Sección "desglose de pendientes por SKU": la suma de "pendiente" de
    # cada fila del resumen debe coincidir exactamente con
    # `PackingResult.unpacked_count`, derivada de la misma fuente (nunca
    # recalculada).
    from uuid import uuid4

    window = MainWindow(app_settings)
    space = _SPACE
    unit_full = LoadUnit(
        sku="FULL-SKU", name="Completo", dimensions=Dimensions3D(10, 10, 10), weight_kg=5.0
    )
    unit_partial = LoadUnit(
        sku="PARTIAL-SKU", name="Parcial", dimensions=Dimensions3D(10, 10, 10), weight_kg=5.0
    )
    window._last_load_units_by_id = {unit_full.id: unit_full, unit_partial.id: unit_partial}

    orientation = Orientation.from_base_dimensions(unit_full.dimensions, OrientationCode.LWH_XYZ)
    placements = (
        Placement(unit_full.id, 1, Position3D(0, 0, 0), orientation, 1),
        Placement(unit_partial.id, 1, Position3D(0, 0, 0), orientation, 2),
    )
    unpacked = (
        UnpackedUnit(unit_partial.id, 2, "no_feasible_position", "sin espacio"),
        UnpackedUnit(unit_partial.id, 3, "no_feasible_position", "sin espacio"),
        UnpackedUnit(uuid4(), 1, "no_feasible_position", "sin espacio"),
    )
    result = PackingResult(
        loading_space=space,
        placements=placements,
        unpacked_units=unpacked,
        requested_count=6,
        packed_count=2,
        used_volume_cm3=2000.0,
        used_weight_kg=10.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
    )

    window._populate_results(result)

    summary_model = window.unpacked_table_panel.pending_summary_model
    assert summary_model.rowCount() == 2  # FULL-SKU nunca aparece
    total_pending_in_summary = sum(
        summary_model.data(summary_model.index(row, 4)) for row in range(summary_model.rowCount())
    )
    assert total_pending_in_summary == result.unpacked_count
    window.close()


def test_pending_tab_label_shows_count_after_populate_results(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Corrección de accesibilidad: la pestaña "No cargados" debe llevar
    # visiblemente el número de unidades pendientes -- antes de esta
    # corrección no había ninguna señal en la pestaña que indicara que
    # había algo que revisar ahí.
    window = MainWindow(app_settings)
    result = _result_with_pending(pending_count=4)
    index = window.results_tabs.indexOf(window.unpacked_table_panel)

    window._populate_results(result)

    assert window.results_tabs.tabText(index) == "No cargados (4)"
    window.close()


def test_pending_tab_label_resets_to_base_text_when_no_pending(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    index = window.results_tabs.indexOf(window.unpacked_table_panel)
    window._populate_results(_result_with_pending(pending_count=3))
    assert window.results_tabs.tabText(index) == "No cargados (3)"

    window._populate_results(_result_with_pending(pending_count=0, packed_count=5))

    assert window.results_tabs.tabText(index) == "No cargados"
    window.close()


def test_reset_to_blank_project_resets_pending_tab_label(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    index = window.results_tabs.indexOf(window.unpacked_table_panel)
    window._populate_results(_result_with_pending(pending_count=7))
    assert window.results_tabs.tabText(index) == "No cargados (7)"

    window._reset_to_blank_project()

    assert window.results_tabs.tabText(index) == "No cargados"
    window.close()


def test_optimization_finished_with_pending_units_switches_to_pending_tab(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Causa real reportada: `_on_optimization_finished` siempre saltaba a
    # "Resumen" (`_on_show_results()` incondicional), así que el
    # desglose por SKU -- ya calculado correctamente -- nunca tenía
    # ninguna vía visible para que el usuario lo descubriera sin saber
    # de antemano que debía hacer clic en "No cargados".
    window = MainWindow(app_settings)
    result = _result_with_pending(pending_count=5)

    window._on_optimization_finished(result)

    assert window.results_tabs.currentWidget() is window.unpacked_table_panel
    window.close()


def test_optimization_finished_without_pending_units_shows_summary_tab(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Sin pendientes, el comportamiento original (ir a "Resumen") se
    # mantiene intacto -- el auto-salto a "No cargados" es condicional,
    # no un cambio general de qué pestaña se muestra al terminar.
    window = MainWindow(app_settings)
    result = _result_with_pending(pending_count=0, packed_count=5)

    window._on_optimization_finished(result)

    assert window.results_tabs.currentWidget() is window.results_panel
    window.close()


def test_optimization_cancelled_with_partial_pending_still_shows_summary_tab(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Una ejecución cancelada normalmente deja instancias "pendientes"
    # que no reflejan un resultado real -- no debe disparar el
    # auto-salto a "No cargados", que está pensado para una
    # optimización completada de verdad.
    window = MainWindow(app_settings)
    window._cancel_requested = True
    result = _result_with_pending(pending_count=5)

    window._on_optimization_finished(result)

    assert window.results_tabs.currentWidget() is window.results_panel
    window.close()


def test_clicking_pending_kpi_tile_navigates_to_pending_tab(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window._populate_results(_result_with_pending(pending_count=2))
    window._on_show_results()
    assert window.results_tabs.currentWidget() is window.results_panel

    window.results_panel.pending_tile_clicked.emit()

    assert window.results_tabs.currentWidget() is window.unpacked_table_panel
    window.close()


def test_pending_summary_table_has_usable_height_once_shown(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Regresión directa del bug reportado: con la altura mínima y el
    # stretch anteriores, `summary_table_view` quedaba en ~30px reales
    # (prácticamente solo la cabecera) sin importar cuánto creciera la
    # ventana. Verificado antes/después con un `PackingResult` real.
    window = MainWindow(app_settings)
    window.resize(1280, 800)
    window.show()
    qapp.processEvents()
    window._populate_results(_result_with_pending(pending_count=4))
    window.results_tabs.setCurrentWidget(window.unpacked_table_panel)
    qapp.processEvents()
    qapp.processEvents()

    assert window.unpacked_table_panel.summary_table_view.height() >= 50
    window.close()


def test_viewer_stays_clearly_dominant_after_pending_visibility_fix(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # El visor 3D debe seguir siendo la zona visual dominante incluso
    # tras aumentar la altura mínima de `results_tabs` para que el
    # resumen de pendientes sea legible -- no se repite la regresión de
    # una fase anterior donde el visor quedó pequeño.
    window = MainWindow(app_settings)
    window.resize(1280, 800)
    window.show()
    qapp.processEvents()
    window._populate_results(_result_with_pending(pending_count=4))
    window.results_tabs.setCurrentWidget(window.unpacked_table_panel)
    qapp.processEvents()
    qapp.processEvents()

    viewer_height, results_height = window.viewer_results_splitter.sizes()
    assert viewer_height > results_height
    # Dominancia clara (~2:1, el stretch nominal es 4:1 pero el mínimo de
    # `results_tabs` recorta algo de esa proporción) -- no una igualdad
    # exacta de píxeles, que dependería de detalles de layout que no son
    # el invariante real que importa aquí.
    assert viewer_height >= 1.9 * results_height
    window.close()
