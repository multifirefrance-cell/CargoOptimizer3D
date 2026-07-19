"""Pruebas de integración: `MainWindow` y el catálogo/perfiles/historial SQLite (fase 7.1).

Usa un `CatalogService` real respaldado por una base SQLite temporal
(nunca la base real del usuario) para la mayoría de las pruebas —
mismo criterio que las pruebas de persistencia `.cargo3d` de la fase
7.0: preferir el camino real sobre mocks siempre que sea seguro y
rápido bajo `offscreen`. Los diálogos de catálogo/perfiles se
sustituyen por dobles simples (nunca se llama a `.exec()` de verdad).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.infrastructure.database.catalog_service import CatalogService
from cargo_optimizer.presentation.desktop import main_window as main_window_module
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import PROFILE_CUSTOM
from cargo_optimizer.presentation.desktop.settings import AppSettings


def _wait_until_worker_finishes(
    app: QApplication, window: MainWindow, timeout_s: float = 15.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while window._optimization_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._optimization_worker is None


def _allow_close_without_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restablece `QMessageBox.question` a "Descartar" antes de cerrar la ventana.

    Varias pruebas de este archivo sustituyen `QMessageBox.question`
    por una respuesta fija (Guardar/GuardarComo) para probar un flujo
    de catálogo/perfiles concreto; si esa sustitución sigue activa al
    llamar a `window.close()`, la confirmación de "cambios sin
    guardar" (no relacionada) reutilizaría esa misma respuesta y podría
    intentar abrir un `QFileDialog` real, que se queda colgado bajo
    `offscreen`. Se restablece aquí a "Descartar" (igual que el valor
    por defecto de `conftest.py`) justo antes de cerrar.
    """

    def _fake(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def _sample_result() -> PackingResult:
    return PackingResult(
        loading_space=LoadingSpace(
            name="Espacio",
            category=LoadingSpaceCategory.WAREHOUSE,
            internal_dimensions=Dimensions3D(100, 100, 100),
        ),
        placements=(),
        unpacked_units=(),
        requested_count=0,
        packed_count=0,
        used_volume_cm3=0.0,
        used_weight_kg=0.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
    )


def _space(**overrides: object) -> LoadingSpace:
    kwargs: dict[str, object] = {
        "name": "Perfil de prueba único",
        "category": LoadingSpaceCategory.WAREHOUSE,
        "internal_dimensions": Dimensions3D(500.0, 300.0, 300.0),
    }
    kwargs.update(overrides)
    return LoadingSpace(**kwargs)  # type: ignore[arg-type]


def _fake_catalog_dialog(accepted: bool, units: tuple[LoadUnit, ...]) -> type:
    # Subclasea QDialog (no `object`): `main_window.py` compara
    # `dialog.exec() != ProductCatalogDialog.DialogCode.Accepted` sobre la
    # propia clase importada, que el monkeypatch sustituye por esta — sin
    # heredar de QDialog no existiría `DialogCode` en la clase sustituta.
    class _Fake(QDialog):
        def __init__(self, parent: object = None, **_kwargs: object) -> None:
            super().__init__(parent)  # type: ignore[arg-type]

        def exec(self) -> int:  # type: ignore[override]
            return int(QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected)

        def selected_units_to_add(self) -> tuple[LoadUnit, ...]:
            return units

    return _Fake


def _fake_profiles_dialog(accepted: bool, space: LoadingSpace | None) -> type:
    class _Fake(QDialog):
        def __init__(self, parent: object = None, **_kwargs: object) -> None:
            super().__init__(parent)  # type: ignore[arg-type]

        def exec(self) -> int:  # type: ignore[override]
            return int(QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected)

        def result_space(self) -> LoadingSpace | None:
            return space

    return _Fake


def test_limited_mode_disables_catalog_and_profile_actions(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    assert window.action_open_catalog.isEnabled() is False
    assert window.action_add_from_catalog.isEnabled() is False
    assert window.action_save_product_to_catalog.isEnabled() is False
    assert window.action_predefined_profiles.isEnabled() is False
    assert window.action_save_as_profile.isEnabled() is False
    window.close()


def test_catalog_available_enables_actions(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    assert window.action_open_catalog.isEnabled() is True
    assert window.action_predefined_profiles.isEnabled() is True
    window.close()


def test_catalog_error_shows_warning_once(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    window = MainWindow(app_settings, catalog_service=None, catalog_error="fallo simulado de disco")

    assert len(warnings) == 1
    assert "fallo simulado de disco" in warnings[0][2]
    assert window.action_open_catalog.isEnabled() is False
    window.close()


def test_on_open_catalog_adds_units_and_marks_dirty(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    monkeypatch.setattr(
        main_window_module,
        "ProductCatalogDialog",
        _fake_catalog_dialog(True, (_unit(sku="CAT-1"),)),
    )

    window._on_open_catalog()

    assert window.product_table_panel.model.rowCount() == 1
    assert window.product_table_panel.model.load_units()[0].sku == "CAT-1"
    assert window._is_dirty is True
    window.close()


def test_on_open_catalog_skips_duplicate_sku_and_warns(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="DUP-1")])
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))
    monkeypatch.setattr(
        main_window_module,
        "ProductCatalogDialog",
        _fake_catalog_dialog(True, (_unit(sku="DUP-1"),)),
    )

    window._on_open_catalog()

    assert window.product_table_panel.model.rowCount() == 1  # no se añadió el duplicado
    assert len(warnings) == 1
    window.close()


def test_on_save_product_to_catalog_creates_new_entry(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="NEW-CAT-1")])
    window.product_table_panel.table_view.selectRow(0)

    window._on_save_product_to_catalog()

    assert service.products.get_by_sku("NEW-CAT-1") is not None
    window.close()


def test_on_save_product_to_catalog_updates_existing_on_save_response(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    service.products.add(_unit(sku="EXISTING-1", weight_kg=1.0))
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="EXISTING-1", weight_kg=42.0)])
    window.product_table_panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Save)
    )

    window._on_save_product_to_catalog()

    updated = service.products.get_by_sku("EXISTING-1")
    assert updated is not None
    assert updated.weight_kg == 42.0
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_on_save_product_to_catalog_save_with_different_sku(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    service.products.add(_unit(sku="EXISTING-2"))
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="EXISTING-2")])
    window.product_table_panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.SaveAll)
    )
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("EXISTING-2-B", True))
    )

    window._on_save_product_to_catalog()

    assert service.products.get_by_sku("EXISTING-2-B") is not None
    assert service.products.get_by_sku("EXISTING-2") is not None  # el original no se toca
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_on_save_product_to_catalog_cancel_leaves_catalog_untouched(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    service.products.add(_unit(sku="EXISTING-3", weight_kg=1.0))
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="EXISTING-3", weight_kg=99.0)])
    window.product_table_panel.table_view.selectRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel)
    )

    window._on_save_product_to_catalog()

    assert service.products.get_by_sku("EXISTING-3").weight_kg == 1.0  # type: ignore[union-attr]
    window.close()


def test_on_open_profiles_applies_chosen_profile_and_marks_dirty(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    chosen = _space(name="Perfil elegido para aplicar")
    monkeypatch.setattr(
        main_window_module, "LoadingSpaceProfilesDialog", _fake_profiles_dialog(True, chosen)
    )

    window._on_open_profiles()

    built = window.loading_space_form_panel.build_loading_space()
    assert built is not None
    assert built.name == "Perfil elegido para aplicar"
    assert built.id != chosen.id  # copia independiente, no el mismo UUID de catálogo
    assert window._is_dirty is True
    window.close()


def test_on_save_as_profile_creates_new_profile(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    window.loading_space_form_panel.set_current_profile_name(PROFILE_CUSTOM)
    window.loading_space_form_panel._name_edit.setText("Mi perfil nuevo y único")

    window._on_save_as_profile()

    assert service.profiles.get_by_name("Mi perfil nuevo y único") is not None
    window.close()


def test_on_save_as_profile_updates_existing_on_save_response(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    service.profiles.add(_space(name="Perfil a actualizar"))
    window = MainWindow(app_settings, catalog_service=service)
    window.loading_space_form_panel.set_current_profile_name(PROFILE_CUSTOM)
    window.loading_space_form_panel._name_edit.setText("Perfil a actualizar")
    window.loading_space_form_panel._length_spin.setValue(777.0)
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Save)
    )

    window._on_save_as_profile()

    updated = service.profiles.get_by_name("Perfil a actualizar")
    assert updated is not None
    assert updated.internal_dimensions.length_cm == 777.0
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_project_open_and_save_record_history(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="HIST-1")])
    path = tmp_path / "proyecto_historial.cargo3d"

    window._save_to_path(path)

    entries = service.project_history.list_recent()
    assert len(entries) == 1
    assert entries[0].file_path == str(path)
    assert entries[0].last_saved_at is not None

    window2 = MainWindow(app_settings, catalog_service=service)
    window2._open_project_from_path(path)

    entries_after_open = service.project_history.list_recent()
    assert len(entries_after_open) == 1  # misma fila, no una nueva
    assert entries_after_open[0].last_opened_at is not None
    window.close()
    window2.close()


def test_successful_optimization_records_run_history(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    window.product_table_panel.model.add_units([_unit(sku="RUN-1"), _unit(sku="RUN-2")])

    window.action_run_optimization.trigger()
    _wait_until_worker_finishes(qapp, window)

    entries = service.run_history.list_for_project(window._current_project_id)
    assert len(entries) == 1
    assert entries[0].requested_count == 2
    window.close()


def test_close_event_disposes_catalog_service(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    calls: list[str] = []
    monkeypatch.setattr(service, "close", lambda: calls.append("closed"))

    window.close()

    assert calls == ["closed"]


def test_sync_catalog_changes_refreshes_quick_add_combo(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    service.products.add(_unit(sku="NEW-CATALOG-SKU"))

    window._sync_catalog_changes()

    assert "new-catalog-sku" in window.product_table_panel.quick_add_panel._by_sku
    window.close()


def test_sync_catalog_changes_updates_a_row_already_in_this_load(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    added = service.products.add(_unit(sku="EDITED-1", weight_kg=10.0, quantity=1))
    window.product_table_panel.model.add_units([CatalogService.copy_to_project(added)])
    service.products.update(_unit(id=added.id, sku="EDITED-1", weight_kg=250.0, quantity=1))

    window._sync_catalog_changes()

    project_unit = window.product_table_panel.model.load_units()[0]
    assert project_unit.weight_kg == 250.0
    window.close()


def test_sync_catalog_changes_invalidates_stale_result_on_geometric_edit(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    added = service.products.add(_unit(sku="EDITED-2", weight_kg=10.0))
    window.product_table_panel.model.add_units([CatalogService.copy_to_project(added)])
    window._last_result = _sample_result()
    window._result_stale = False
    service.products.update(_unit(id=added.id, sku="EDITED-2", weight_kg=500.0))

    window._sync_catalog_changes()

    assert window._result_stale is True
    assert window.results_panel._stale_label.isHidden() is False
    window.close()


def test_sync_catalog_changes_color_only_edit_does_not_invalidate_but_recolors_viewer(
    qapp: QApplication,
    app_settings: AppSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    added = service.products.add(_unit(sku="EDITED-3", color_hex="#111111"))
    project_unit = CatalogService.copy_to_project(added)
    window.product_table_panel.model.add_units([project_unit])
    window._last_result = _sample_result()
    window._result_stale = False
    window._last_load_units_by_id = {project_unit.id: project_unit}
    display_calls: list[object] = []
    monkeypatch.setattr(
        window.viewer_widget, "display_result", lambda *a, **k: display_calls.append(a)
    )
    service.products.update(_unit(id=added.id, sku="EDITED-3", color_hex="#ABCDEF"))

    window._sync_catalog_changes()

    assert window._result_stale is False
    assert window.results_panel._stale_label.isHidden() is True
    assert len(display_calls) == 1
    assert window._last_load_units_by_id[project_unit.id].color_hex == "#ABCDEF"
    window.close()


def test_on_open_catalog_syncs_changes_even_when_dialog_is_closed_without_adding(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    window = MainWindow(app_settings, catalog_service=service)
    added = service.products.add(_unit(sku="EDITED-4", weight_kg=10.0))
    window.product_table_panel.model.add_units([CatalogService.copy_to_project(added)])
    service.products.update(_unit(id=added.id, sku="EDITED-4", weight_kg=321.0))
    monkeypatch.setattr(main_window_module, "ProductCatalogDialog", _fake_catalog_dialog(False, ()))

    window._on_open_catalog()

    assert window.product_table_panel.model.load_units()[0].weight_kg == 321.0
    window.close()
