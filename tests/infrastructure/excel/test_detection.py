"""Pruebas de `detection.py`: identificación automática del tipo de plantilla por cabeceras."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from cargo_optimizer.infrastructure.excel.detection import detect_template_kind
from cargo_optimizer.infrastructure.excel.exceptions import ExcelFileError
from cargo_optimizer.infrastructure.excel.templates import (
    CATALOG_TEMPLATE_FILENAME,
    LOADING_SPACE_TEMPLATE_FILENAME,
    PACKING_LIST_TEMPLATE_FILENAME,
    generate_all_templates,
)


def test_detects_each_official_template(tmp_path: Path) -> None:
    generate_all_templates(tmp_path, application_version="9.9.9")

    assert detect_template_kind(tmp_path / CATALOG_TEMPLATE_FILENAME) == "catalog"
    assert detect_template_kind(tmp_path / PACKING_LIST_TEMPLATE_FILENAME) == "packing_list"
    assert detect_template_kind(tmp_path / LOADING_SPACE_TEMPLATE_FILENAME) == "loading_space"


def test_returns_none_for_an_unrecognized_file(tmp_path: Path) -> None:
    path = tmp_path / "desconocido.xlsx"
    workbook = Workbook()
    workbook.active.append(["Columna A", "Columna B"])
    workbook.save(path)

    assert detect_template_kind(path) is None


def test_raises_for_a_corrupt_file(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupto.xlsx"
    corrupt.write_text("no es un xlsx", encoding="utf-8")
    with pytest.raises(ExcelFileError):
        detect_template_kind(corrupt)
