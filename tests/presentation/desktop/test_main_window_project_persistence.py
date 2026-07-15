"""Pruebas de integración: ciclo de vida de proyectos `.cargo3d` en `MainWindow` (fase 7.0).

`QMessageBox.warning`/`.critical`/`.question` son modales: en un entorno
sin usuario (como esta suite, con la plataforma Qt `offscreen`) se
quedan esperando un clic que nunca llega y la prueba se cuelga. Cada
prueba que puede disparar uno lo sustituye por `monkeypatch`.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import AppSettings

_APP_VERSION_PATTERN = "CargoOptimizer3D v"


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


def _answer_question_with(
    monkeypatch: pytest.MonkeyPatch, button: QMessageBox.StandardButton
) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        calls.append(args)
        return button

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))
    return calls


def _add_two_products(window: MainWindow) -> None:
    window.product_table_panel.model.add_default_product()
    window.product_table_panel.model.add_default_product()


def test_new_window_starts_clean_with_untitled_title(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window._is_dirty is False
    assert "Proyecto sin guardar" in window.windowTitle()
    assert "*" not in window.windowTitle()
    window.close()


def test_editing_product_table_marks_project_dirty(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    window.product_table_panel.model.add_default_product()

    assert window._is_dirty is True
    assert window.windowTitle().endswith("*")
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()


def test_editing_loading_space_marks_project_dirty(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    window.loading_space_form_panel._length_spin.setValue(999.0)

    assert window._is_dirty is True
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()


def test_save_project_writes_file_and_marks_clean(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "mi_proyecto.cargo3d"

    saved = window._save_to_path(path)

    assert saved is True
    assert path.exists()
    assert window._is_dirty is False
    assert window._current_project_path == path
    assert "mi_proyecto" in window.windowTitle()
    assert "*" not in window.windowTitle()
    window.close()


def test_save_project_adds_to_recent_files(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "reciente.cargo3d"

    window._save_to_path(path)

    assert str(path) in app_settings.recent_project_files()
    window.close()


def test_open_project_restores_products_space_and_result(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "proyecto.cargo3d"
    window._save_to_path(path)

    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)
    window._save_to_path(path)

    window2 = MainWindow(app_settings)
    window2._open_project_from_path(path)

    assert window2.product_table_panel.model.rowCount() == 2
    assert window2.loading_space_form_panel.build_loading_space() is not None
    assert window2._last_result is not None
    assert window2._last_result.requested_count == 2
    assert window2._is_dirty is False
    assert window2._current_project_path == path
    window.close()
    window2.close()


def test_open_project_restores_results_panel_and_unpacked_table(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "proyecto.cargo3d"
    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)
    window._save_to_path(path)

    window2 = MainWindow(app_settings)
    window2._open_project_from_path(path)

    assert window2.results_panel._requested_label.text() == "2"
    assert window2.results_panel._packed_label.text() != "—"
    window.close()
    window2.close()


def test_open_project_restores_viewer_display_result(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "proyecto.cargo3d"
    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)
    window._save_to_path(path)

    window2 = MainWindow(app_settings)
    received: list[tuple[Any, Any]] = []
    monkeypatch.setattr(
        window2.viewer_widget,
        "display_result",
        lambda result, load_units_by_id: received.append((result, load_units_by_id)),
    )

    window2._open_project_from_path(path)

    assert len(received) == 1
    assert received[0][0] == window2._last_result
    window.close()
    window2.close()


def test_open_project_without_a_result_clears_viewer_and_results(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "sin_resultado.cargo3d"
    window._save_to_path(path)

    window2 = MainWindow(app_settings)
    window2._open_project_from_path(path)

    assert window2._last_result is None
    assert window2.results_panel._requested_label.text() == "—"
    window.close()
    window2.close()


def test_modifying_project_after_result_invalidates_it(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)

    assert window._result_stale is False

    window.product_table_panel.model.add_default_product()

    assert window._result_stale is True
    assert window.results_panel._stale_label.isHidden() is False
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()


def test_running_a_fresh_optimization_clears_stale_flag(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)
    window.product_table_panel.model.add_default_product()
    assert window._result_stale is True

    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)

    assert window._result_stale is False
    assert window.results_panel._stale_label.isHidden() is True
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()


def test_stale_result_round_trips_through_save_and_load(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)
    window.product_table_panel.model.add_default_product()
    assert window._result_stale is True

    path = tmp_path / "proyecto_desactualizado.cargo3d"
    window._save_to_path(path)

    window2 = MainWindow(app_settings)
    window2._open_project_from_path(path)

    assert window2._result_stale is True
    assert window2.results_panel._stale_label.isHidden() is False
    window.close()
    window2.close()


def test_new_project_resets_everything(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "proyecto.cargo3d"
    window._save_to_path(path)

    window.action_new.trigger()

    assert window.product_table_panel.model.rowCount() == 0
    assert window._current_project_path is None
    assert window._is_dirty is False
    assert window._last_result is None
    assert "Proyecto sin guardar" in window.windowTitle()
    window.close()


def test_new_project_prompts_when_dirty_and_respects_cancel(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    assert window._is_dirty is True
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Cancel)

    window.action_new.trigger()

    assert window.product_table_panel.model.rowCount() == 2  # cancelado: nada cambió
    assert window._is_dirty is True
    window.close()


def test_close_project_action_resets_to_blank_state(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "proyecto.cargo3d"
    window._save_to_path(path)

    window.action_close_project.trigger()

    assert window._current_project_path is None
    assert window.product_table_panel.model.rowCount() == 0
    window.close()


def test_confirm_discard_returns_true_when_not_dirty(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window._confirm_discard_unsaved_changes() is True
    window.close()


def test_confirm_discard_cancel_blocks_and_does_not_touch_state(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Cancel)

    result = window._confirm_discard_unsaved_changes()

    assert result is False
    assert window._is_dirty is True
    window.close()


def test_confirm_discard_discard_allows_continuing_without_saving(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)

    result = window._confirm_discard_unsaved_changes()

    assert result is True
    assert window._is_dirty is True  # discard no guarda, pero permite continuar
    window.close()


def test_close_event_blocks_when_user_cancels_discard(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Cancel)

    assert window.close() is False

    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    assert window.close() is True


def test_recent_files_menu_lists_saved_projects(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "reciente.cargo3d"
    window._save_to_path(path)

    window._rebuild_recent_projects_menu()

    action_texts = [action.text() for action in window.menu_recent_projects.actions()]
    assert path.name in action_texts
    window.close()


def test_recent_files_menu_drops_deleted_paths(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings)
    _add_two_products(window)
    path = tmp_path / "borrado.cargo3d"
    window._save_to_path(path)
    path.unlink()

    window._rebuild_recent_projects_menu()

    assert path.name not in [action.text() for action in window.menu_recent_projects.actions()]
    window.close()


def test_invalid_project_file_shows_error_and_does_not_crash(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors = _silence_message_box(monkeypatch, "critical")
    path = tmp_path / "corrupto.cargo3d"
    path.write_text("esto no es json", encoding="utf-8")

    window = MainWindow(app_settings)
    window._open_project_from_path(path)

    assert len(errors) == 1
    assert window._current_project_path is None
    window.close()


def test_saving_with_incomplete_loading_space_shows_warning(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings = _silence_message_box(monkeypatch, "warning")
    window = MainWindow(app_settings)
    window.loading_space_form_panel.set_current_profile_name("Personalizado")
    window.loading_space_form_panel._name_edit.setText("")

    saved = window._save_to_path(tmp_path / "invalido.cargo3d")

    assert saved is False
    assert len(warnings) == 1
    _answer_question_with(monkeypatch, QMessageBox.StandardButton.Discard)
    window.close()
