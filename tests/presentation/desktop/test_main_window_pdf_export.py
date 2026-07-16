"""Pruebas de integración: `MainWindow` y `infrastructure/pdf` (fase 9.1).

Bajo `QT_QPA_PLATFORM=offscreen` el visor 3D nunca está disponible
(ver `docs/ThreeDViewer.md`), así que `viewer_widget.export_screenshot_png()`
siempre devuelve `None` en esta suite — cubre exactamente el caso "sin
captura del visor" que el informe debe soportar sin error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.infrastructure.pdf.templates import BUILTIN_TEMPLATES
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import AppSettings


def _fake_save_dialog(path: Path | None) -> Any:
    text = str(path) if path is not None else ""
    return staticmethod(lambda *a, **k: (text, ""))


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


def test_on_export_pdf_warns_when_no_result(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    warnings: list[tuple[Any, ...]] = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a)))

    window._on_export_pdf()

    assert len(warnings) == 1
    window.close()


def test_on_export_pdf_cancel_in_type_selection_writes_nothing(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    window._last_result = _sample_result()
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False)))
    out_path = tmp_path / "no_deberia_existir.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save_dialog(out_path))

    window._on_export_pdf()

    assert not out_path.exists()
    window.close()


def test_on_export_pdf_cancel_in_save_dialog_writes_nothing(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    window._last_result = _sample_result()
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *a, **k: (BUILTIN_TEMPLATES[0].display_name, True)),
    )
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save_dialog(None))

    window._on_export_pdf()

    assert list(tmp_path.iterdir()) == []
    window.close()


@pytest.mark.parametrize("template", BUILTIN_TEMPLATES, ids=lambda t: t.key)
def test_on_export_pdf_writes_a_valid_pdf_for_each_report_type(
    template: Any,
    qapp: QApplication,
    app_settings: AppSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    window._last_result = _sample_result()
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *a, **k: (template.display_name, True))
    )
    out_path = tmp_path / f"{template.key}.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save_dialog(out_path))

    window._on_export_pdf()

    assert out_path.exists()
    reader = PdfReader(str(out_path))
    assert len(reader.pages) >= 1
    window.close()


def test_on_export_pdf_adds_pdf_suffix_when_missing(
    qapp: QApplication, app_settings: AppSettings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    window._last_result = _sample_result()
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *a, **k: (BUILTIN_TEMPLATES[0].display_name, True)),
    )
    out_path_no_suffix = tmp_path / "informe_sin_extension"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", _fake_save_dialog(out_path_no_suffix))

    window._on_export_pdf()

    assert (tmp_path / "informe_sin_extension.pdf").exists()
    window.close()


def test_on_export_pdf_disabled_while_optimizing(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings, catalog_service=None)
    assert window.action_export_pdf.isEnabled() is True

    window._set_running_controls_enabled(False)
    assert window.action_export_pdf.isEnabled() is False

    window._set_running_controls_enabled(True)
    assert window.action_export_pdf.isEnabled() is True
    window.close()
