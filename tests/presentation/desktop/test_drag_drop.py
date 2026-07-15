"""Pruebas de `drag_drop.py`: detección de `.xlsx` local en eventos de arrastrar/soltar (fase 8.1).

Se usa un doble ligero con solo `mimeData()` en vez de un `QDropEvent`
real: las tres funciones de `drag_drop.py` solo llaman a ese método, y
construir eventos Qt reales de arrastre añadiría complejidad sin
aportar cobertura adicional.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.drag_drop import (
    all_excel_paths,
    first_excel_path,
    has_excel_url,
)


class _FakeEvent:
    def __init__(self, mime_data: QMimeData) -> None:
        self._mime_data = mime_data

    def mimeData(self) -> QMimeData:  # noqa: N802
        return self._mime_data


def _mime_data_with_paths(paths: list[Path]) -> QMimeData:
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    return mime_data


def test_has_excel_url_true_for_local_xlsx(qapp: QApplication, tmp_path: Path) -> None:
    event = _FakeEvent(_mime_data_with_paths([tmp_path / "archivo.xlsx"]))

    assert has_excel_url(event) is True  # type: ignore[arg-type]


def test_has_excel_url_false_when_no_urls(qapp: QApplication) -> None:
    event = _FakeEvent(QMimeData())

    assert has_excel_url(event) is False  # type: ignore[arg-type]


def test_has_excel_url_false_for_non_xlsx_file(qapp: QApplication, tmp_path: Path) -> None:
    event = _FakeEvent(_mime_data_with_paths([tmp_path / "archivo.pdf"]))

    assert has_excel_url(event) is False  # type: ignore[arg-type]


def test_has_excel_url_is_case_insensitive_on_extension(qapp: QApplication, tmp_path: Path) -> None:
    event = _FakeEvent(_mime_data_with_paths([tmp_path / "ARCHIVO.XLSX"]))

    assert has_excel_url(event) is True  # type: ignore[arg-type]


def test_first_excel_path_returns_first_local_xlsx(qapp: QApplication, tmp_path: Path) -> None:
    paths = [tmp_path / "a.xlsx", tmp_path / "b.xlsx"]
    event = _FakeEvent(_mime_data_with_paths(paths))

    result = first_excel_path(event)  # type: ignore[arg-type]

    assert result == paths[0]


def test_first_excel_path_none_when_no_xlsx(qapp: QApplication, tmp_path: Path) -> None:
    event = _FakeEvent(_mime_data_with_paths([tmp_path / "a.pdf"]))

    assert first_excel_path(event) is None  # type: ignore[arg-type]


def test_all_excel_paths_returns_every_local_xlsx_ignoring_others(
    qapp: QApplication, tmp_path: Path
) -> None:
    paths = [tmp_path / "a.xlsx", tmp_path / "b.pdf", tmp_path / "c.xlsx"]
    event = _FakeEvent(_mime_data_with_paths(paths))

    result = all_excel_paths(event)  # type: ignore[arg-type]

    assert result == [paths[0], paths[2]]


def test_all_excel_paths_empty_when_no_urls(qapp: QApplication) -> None:
    event = _FakeEvent(QMimeData())

    assert all_excel_paths(event) == []  # type: ignore[arg-type]
