"""Pruebas de `ImportPreviewDialog`: contadores, modo de importación parcial, selección (8.1)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.import_preview import CatalogImportPreview
from cargo_optimizer.infrastructure.excel.results import RowError
from cargo_optimizer.presentation.desktop.dialogs.import_preview_dialog import ImportPreviewDialog


def _unit(sku: str) -> LoadUnit:
    return LoadUnit(
        sku=sku, name=f"Producto {sku}", dimensions=Dimensions3D(50, 40, 30), weight_kg=10.0
    )


def _preview(**overrides: object) -> CatalogImportPreview:
    kwargs: dict[str, object] = {
        "row_count": 2,
        "column_count": 16,
        "new_units": (_unit("NEW-1"),),
        "existing_units": (_unit("EXISTING-1"),),
        "duplicate_errors": (),
        "invalid_errors": (),
    }
    kwargs.update(overrides)
    return CatalogImportPreview(**kwargs)  # type: ignore[arg-type]


def test_default_mode_is_all_rows(qapp: QApplication) -> None:
    dialog = ImportPreviewDialog(None, preview=_preview())

    dialog._on_accept()

    assert dialog.result_selection_mode() == "all"
    assert dialog.result_selected_skus() is None


def test_selecting_a_mode_updates_the_result(qapp: QApplication) -> None:
    dialog = ImportPreviewDialog(None, preview=_preview())

    dialog._mode_combo.setCurrentText("Solo productos nuevos")
    dialog._on_accept()

    assert dialog.result_selection_mode() == "new_only"


def test_selected_mode_returns_only_checked_skus(qapp: QApplication) -> None:
    dialog = ImportPreviewDialog(None, preview=_preview())
    dialog._mode_combo.setCurrentText("Solo filas seleccionadas")
    # Desmarca el segundo elemento (EXISTING-1), deja marcado NEW-1.
    dialog._selection_list.item(1).setCheckState(Qt.CheckState.Unchecked)

    dialog._on_accept()

    assert dialog.result_selection_mode() == "selected"
    assert dialog.result_selected_skus() == frozenset({"NEW-1"})


def test_cancel_leaves_selection_mode_as_none(qapp: QApplication) -> None:
    dialog = ImportPreviewDialog(None, preview=_preview())

    dialog.reject()

    assert dialog.result_selection_mode() is None


def test_construction_does_not_fail_when_preview_has_invalid_rows(qapp: QApplication) -> None:
    preview = _preview(invalid_errors=(RowError(4, "'Largo (cm)' no es un numero valido."),))

    dialog = ImportPreviewDialog(None, preview=preview)

    assert dialog.isVisible() is False
    assert preview.invalid_count == 1
