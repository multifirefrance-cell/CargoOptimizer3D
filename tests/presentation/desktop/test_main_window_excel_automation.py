"""Pruebas de integración: `MainWindow` y el flujo Excel automatizado (fase 8.1).

Cubre el mapeo de columnas, la resolución de duplicados, la
importación parcial, la importación masiva y el arrastrar y soltar
sobre `MainWindow` y `ProductCatalogDialog` — mismo criterio que
`test_main_window_excel_integration.py` (fase 8.0): archivos `.xlsx`
reales sobre `tmp_path`, un `CatalogService` real respaldado por SQLite
temporal, y solo se sustituyen diálogos Qt (nunca el motor real).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.catalog_service import CatalogService
from cargo_optimizer.infrastructure.excel.catalog_exporter import export_catalog
from cargo_optimizer.infrastructure.excel.product_rows import PRODUCT_COLUMNS
from cargo_optimizer.presentation.desktop.dialogs.column_mapping_dialog import ColumnMappingDialog
from cargo_optimizer.presentation.desktop.dialogs.duplicate_resolution_dialog import (
    DuplicateResolutionDialog,
)
from cargo_optimizer.presentation.desktop.dialogs.import_preview_dialog import ImportPreviewDialog
from cargo_optimizer.presentation.desktop.dialogs.product_catalog_dialog import ProductCatalogDialog
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import AppSettings


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def _kupfer_style_file(path: Path, *, sku: str = "KUP-1") -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Código", "Descripción", "Largo", "Ancho", "Alto", "Peso bruto", "Cantidad"])
    worksheet.append([sku, "Caja Kupfer", 50, 40, 30, 12.5, 3])
    workbook.save(path)


def _official_catalog_file(path: Path, *, sku: str = "OFICIAL-1") -> None:
    export_catalog([_unit(sku=sku)], path)


def _accept_mapping_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ColumnMappingDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(
        ColumnMappingDialog, "result_mapping", lambda self: dict(self._current_mapping())
    )


def _cancel_mapping_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ColumnMappingDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(ColumnMappingDialog, "result_mapping", lambda self: None)


def _accept_preview_dialog(
    monkeypatch: pytest.MonkeyPatch, *, mode: str = "all", selected_skus: object = None
) -> None:
    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(ImportPreviewDialog, "result_selection_mode", lambda self: mode)
    monkeypatch.setattr(ImportPreviewDialog, "result_selected_skus", lambda self: selected_skus)


def _cancel_preview_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ImportPreviewDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(ImportPreviewDialog, "result_selection_mode", lambda self: None)
    monkeypatch.setattr(ImportPreviewDialog, "result_selected_skus", lambda self: None)


def _accept_duplicate_dialog(monkeypatch: pytest.MonkeyPatch, resolutions: dict[str, str]) -> None:
    monkeypatch.setattr(DuplicateResolutionDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(
        DuplicateResolutionDialog, "result_resolutions", lambda self: dict(resolutions)
    )


def _no_save_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    )


def test_smart_import_fully_recognized_file_skips_mapping_dialog(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "oficial.xlsx"
    _official_catalog_file(path)
    # Si se abriera el diálogo de mapeo, este monkeypatch haría fallar la prueba.
    monkeypatch.setattr(
        ColumnMappingDialog,
        "exec",
        lambda self: (_ for _ in ()).throw(AssertionError("no debería abrirse")),
    )
    _accept_preview_dialog(monkeypatch)
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert report.imported_count == 1
    assert service.products.get_by_sku("OFICIAL-1") is not None
    window.close()


def test_smart_import_unrecognized_headers_opens_mapping_dialog(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "parcial.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Código", "Descripción", "Largo", "Ancho", "Alto", "Peso bruto", "Almacen"])
    worksheet.append(["PART-1", "Producto parcial", 50, 40, 30, 12.5, "Nave 3"])
    workbook.save(path)
    _accept_mapping_dialog(monkeypatch)
    _accept_preview_dialog(monkeypatch)
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert report.imported_count == 1
    assert service.products.get_by_sku("PART-1") is not None
    window.close()


def test_smart_import_force_mapping_dialog_even_when_fully_recognized(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "oficial.xlsx"
    _official_catalog_file(path)
    opened: list[bool] = []

    def _exec(self: ColumnMappingDialog) -> QDialog.DialogCode:
        opened.append(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ColumnMappingDialog, "exec", _exec)
    monkeypatch.setattr(
        ColumnMappingDialog, "result_mapping", lambda self: dict(self._current_mapping())
    )
    _accept_preview_dialog(monkeypatch)
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True, force_mapping_dialog=True)

    assert opened == [True]
    assert report is not None
    assert report.imported_count == 1
    window.close()


def test_smart_import_cancel_in_mapping_dialog_aborts_everything(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "parcial.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Almacen", "Zona"])
    worksheet.append(["Nave 3", "A"])
    workbook.save(path)
    _cancel_mapping_dialog(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is None
    assert service.products.count_active() == 0
    window.close()


def test_smart_import_cancel_in_preview_dialog_aborts_everything(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "oficial.xlsx"
    _official_catalog_file(path)
    _cancel_preview_dialog(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is None
    assert service.products.count_active() == 0
    window.close()


def test_smart_import_partial_new_only_mode_skips_existing(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="EXISTING-1", name="Original"))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "mixto.xlsx"
    export_catalog([_unit(sku="EXISTING-1", name="Del archivo"), _unit(sku="NEW-1")], path)
    _accept_preview_dialog(monkeypatch, mode="new_only")
    # El archivo trae un SKU ya existente: aunque el modo "solo nuevos" lo
    # descarte después, la clasificación previa igual dispara el diálogo de
    # duplicados y hay que responderlo para no colgar el proceso bajo offscreen.
    _accept_duplicate_dialog(monkeypatch, {"EXISTING-1": "ignore"})
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert service.products.get_by_sku("NEW-1") is not None
    existing = service.products.get_by_sku("EXISTING-1")
    assert existing is not None
    assert existing.name == "Original"  # no tocado: modo "solo nuevos"
    window.close()


def test_smart_import_duplicate_resolution_update(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="EXISTING-1", name="Original", weight_kg=10.0))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "actualiza.xlsx"
    export_catalog([_unit(sku="EXISTING-1", name="Actualizado", weight_kg=55.0)], path)
    _accept_preview_dialog(monkeypatch)
    _accept_duplicate_dialog(monkeypatch, {"EXISTING-1": "update"})
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert report.updated_count == 1
    updated = service.products.get_by_sku("EXISTING-1")
    assert updated is not None
    assert updated.name == "Actualizado"
    assert updated.weight_kg == 55.0
    window.close()


def test_smart_import_duplicate_resolution_duplicate_creates_new_sku(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="EXISTING-1"))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "duplicar.xlsx"
    export_catalog([_unit(sku="EXISTING-1")], path)
    _accept_preview_dialog(monkeypatch)
    _accept_duplicate_dialog(monkeypatch, {"EXISTING-1": "duplicate"})
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert service.products.get_by_sku("EXISTING-1-DUP") is not None
    assert service.products.count_active() == 2
    window.close()


def test_smart_import_duplicate_resolution_ignore_leaves_catalog_untouched(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="EXISTING-1", name="Original"))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "ignorar.xlsx"
    export_catalog([_unit(sku="EXISTING-1", name="Del archivo")], path)
    _accept_preview_dialog(monkeypatch)
    _accept_duplicate_dialog(monkeypatch, {"EXISTING-1": "ignore"})
    _no_save_report(monkeypatch)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is not None
    assert report.ignored_count == 1
    existing = service.products.get_by_sku("EXISTING-1")
    assert existing is not None
    assert existing.name == "Original"
    window.close()


def test_smart_import_cancel_in_duplicate_dialog_aborts_everything(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="EXISTING-1", name="Original"))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "cancelar.xlsx"
    export_catalog([_unit(sku="EXISTING-1", name="Del archivo")], path)
    _accept_preview_dialog(monkeypatch)
    monkeypatch.setattr(DuplicateResolutionDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    monkeypatch.setattr(DuplicateResolutionDialog, "result_resolutions", lambda self: None)

    report = window._run_smart_catalog_import(path, interactive=True)

    assert report is None
    existing = service.products.get_by_sku("EXISTING-1")
    assert existing is not None
    assert existing.name == "Original"
    window.close()


def test_bulk_import_one_catalog_file_is_never_interactive(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "masivo.xlsx"
    _official_catalog_file(path, sku="BULK-1")
    monkeypatch.setattr(
        ColumnMappingDialog,
        "exec",
        lambda self: (_ for _ in ()).throw(AssertionError("no debería abrirse")),
    )
    monkeypatch.setattr(
        ImportPreviewDialog,
        "exec",
        lambda self: (_ for _ in ()).throw(AssertionError("no debería abrirse")),
    )

    report = window._bulk_import_one_catalog_file(path)

    assert report.imported_count == 1
    assert service.products.get_by_sku("BULK-1") is not None
    window.close()


def test_bulk_import_default_resolution_updates_existing_sku(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    service.products.add(_unit(sku="BULK-EXISTING", weight_kg=1.0))
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "masivo.xlsx"
    export_catalog([_unit(sku="BULK-EXISTING", weight_kg=42.0)], path)

    report = window._bulk_import_one_catalog_file(path)

    assert report.updated_count == 1
    updated = service.products.get_by_sku("BULK-EXISTING")
    assert updated is not None
    assert updated.weight_kg == 42.0
    window.close()


def test_main_window_drop_of_catalog_shaped_file_adds_to_project_not_catalog(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    path = tmp_path / "catalogo.xlsx"
    export_catalog([_unit(sku="DROP-1")], path)

    window._handle_dropped_excel_file(path)

    assert window.product_table_panel.model.rowCount() == 1
    assert window.product_table_panel.model.load_units()[0].sku == "DROP-1"
    window.close()


def test_main_window_drop_of_unrecognized_but_aliasable_file_opens_mapping_dialog(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "kupfer.xlsx"
    _kupfer_style_file(path)
    _accept_mapping_dialog(monkeypatch)

    window._handle_dropped_excel_file(path)

    units = window.product_table_panel.model.load_units()
    assert len(units) == 1
    assert units[0].sku == "KUP-1"
    # El destino es el proyecto, no el catálogo SQLite.
    assert service.products.count_active() == 0
    window.close()


def test_main_window_drop_of_totally_unrecognized_file_warns(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    path = tmp_path / "desconocido.xlsx"
    workbook = Workbook()
    workbook.active.append(["Columna A", "Columna B"])
    workbook.active.append(["x", "y"])
    workbook.save(path)
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(window, "_show_warning", lambda *a, **k: warnings.append(a))

    window._handle_dropped_excel_file(path)

    assert len(warnings) == 1
    window.close()


def test_main_window_drop_without_catalog_service_warns_instead_of_mapping(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    path = tmp_path / "kupfer.xlsx"
    _kupfer_style_file(path)
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(window, "_show_warning", lambda *a, **k: warnings.append(a))

    window._handle_dropped_excel_file(path)

    assert len(warnings) == 1
    window.close()


def test_product_catalog_dialog_drop_imports_into_sqlite_catalog(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogService.create_default(base_dir=tmp_path / "db")
    window = MainWindow(app_settings, catalog_service=service)
    path = tmp_path / "catalogo.xlsx"
    export_catalog([_unit(sku="DIALOG-DROP-1")], path)
    _accept_preview_dialog(monkeypatch)
    _no_save_report(monkeypatch)
    dialog = ProductCatalogDialog(
        window,
        repository=service.products,
        on_excel_dropped=lambda p: window._on_catalog_dialog_excel_dropped(p, dialog),
    )

    window._on_catalog_dialog_excel_dropped(path, dialog)

    assert service.products.get_by_sku("DIALOG-DROP-1") is not None
    # No debe tocar el proyecto abierto.
    assert window.product_table_panel.model.rowCount() == 0
    window.close()


def test_import_catalog_actions_use_the_same_column_layout_as_the_template() -> None:
    # Ancla de regresión: si `product_rows.PRODUCT_COLUMNS` cambia de orden o
    # longitud sin actualizar `mapping.py`, este test debe fallar primero.
    assert len(PRODUCT_COLUMNS) == 16
