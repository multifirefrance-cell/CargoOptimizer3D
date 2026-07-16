"""Pruebas de `report_builder.py`: los cinco informes, imagen 3D, logo, escritura atómica."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image as PILImage
from pypdf import PdfReader

from cargo_optimizer.infrastructure.pdf.exceptions import PdfConfigError
from cargo_optimizer.infrastructure.pdf.report_builder import generate_report
from cargo_optimizer.infrastructure.pdf.report_config import (
    ClientInfo,
    CompanyProfile,
    ReportConfig,
)
from cargo_optimizer.infrastructure.pdf.report_content import build_report_content
from cargo_optimizer.infrastructure.pdf.templates import (
    BUILTIN_TEMPLATES,
    CLIENT_REPORT,
    EXECUTIVE_SUMMARY,
    INTERNAL_DIAGNOSTIC,
    TECHNICAL_FULL,
    ReportTemplate,
)
from tests.infrastructure.pdf._helpers import make_empty_result, make_full_result, make_large_result


def _make_minimal_png() -> bytes:
    """Un PNG válido de 4x4 píxeles, suficiente para que `reportlab.platypus.Image` lo abra."""
    buffer = BytesIO()
    PILImage.new("RGB", (4, 4), color=(31, 56, 100)).save(buffer, format="PNG")
    return buffer.getvalue()


_MINIMAL_PNG = _make_minimal_png()


def _default_config(**overrides: object) -> ReportConfig:
    config = ReportConfig(company=CompanyProfile(name="CargoOptimizer3D"))
    return replace(config, **overrides) if overrides else config


@pytest.mark.parametrize("template", BUILTIN_TEMPLATES, ids=lambda t: t.key)
def test_generate_report_produces_a_valid_pdf_for_each_official_template(
    template: ReportTemplate, tmp_path: Path
) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto de prueba", application_version="9.9.9"
    )
    out_path = tmp_path / f"{template.key}.pdf"

    generate_report(content, template, _default_config(), out_path)

    assert out_path.exists()
    reader = PdfReader(str(out_path))
    assert len(reader.pages) >= 1


def test_generate_report_without_viewer_image_never_errors(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    assert content.viewer_screenshot_png is None

    out_path = tmp_path / "sin_imagen.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    assert out_path.exists()


def test_generate_report_with_viewer_image_includes_it(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result,
        load_units_by_id,
        project_name="Proyecto",
        application_version="9.9.9",
        viewer_screenshot_png=_MINIMAL_PNG,
    )

    out_path = tmp_path / "con_imagen.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    assert out_path.exists()
    reader = PdfReader(str(out_path))
    assert len(reader.pages) >= 1


def test_generate_report_with_corrupt_viewer_image_never_errors(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result,
        load_units_by_id,
        project_name="Proyecto",
        application_version="9.9.9",
        viewer_screenshot_png=b"esto no es un png valido",
    )

    out_path = tmp_path / "imagen_corrupta.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    assert out_path.exists()


def test_generate_report_missing_logo_never_errors(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    config = _default_config(
        company=CompanyProfile(name="Empresa", logo_path=Path("C:/no/existe/logo.png"))
    )

    out_path = tmp_path / "logo_ausente.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, config, out_path)

    assert out_path.exists()


def test_generate_report_existing_logo_is_included(tmp_path: Path) -> None:
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(_MINIMAL_PNG)
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    config = _default_config(company=CompanyProfile(name="Empresa", logo_path=logo_path))

    out_path = tmp_path / "logo_existente.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, config, out_path)

    assert out_path.exists()
    reader = PdfReader(str(out_path))
    assert len(reader.pages) >= 1


def test_generate_report_empty_project(tmp_path: Path) -> None:
    empty_result, load_units_by_id = make_empty_result()
    content = build_report_content(
        empty_result, load_units_by_id, project_name="Proyecto vacío", application_version="9.9.9"
    )

    out_path = tmp_path / "vacio.pdf"
    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    assert out_path.exists()
    reader = PdfReader(str(out_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    # El resumen ejecutivo no lleva tabla de productos, así que este texto nunca debería aparecer.
    assert "No hay productos cargados" not in text


def test_generate_report_full_project_lists_products(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto completo", application_version="9.9.9"
    )
    out_path = tmp_path / "completo.pdf"

    generate_report(content, TECHNICAL_FULL, _default_config(), out_path)

    reader = PdfReader(str(out_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "SKU-1" in text


def test_generate_report_client_report_hides_position_columns(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    config = _default_config(client=ClientInfo(name="Cliente de prueba", reference="PO-123"))
    out_path = tmp_path / "cliente.pdf"

    generate_report(content, CLIENT_REPORT, config, out_path)

    reader = PdfReader(str(out_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Cliente de prueba" in text
    assert "Orientación" not in text  # oculto para el informe de cliente


def test_generate_report_multi_page_numbering(tmp_path: Path) -> None:
    """Muchas filas fuerzan varias páginas; la numeración debe reflejarlo."""
    result, load_units_by_id = make_large_result(box_count=80)
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto grande", application_version="9.9.9"
    )
    out_path = tmp_path / "muchas_paginas.pdf"

    generate_report(content, TECHNICAL_FULL, _default_config(), out_path)

    reader = PdfReader(str(out_path))
    assert len(reader.pages) > 1
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "Página 1 de" in text
    assert f"Página {len(reader.pages)} de {len(reader.pages)}" in text


def test_generate_report_watermark_appears_for_internal_diagnostic(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    out_path = tmp_path / "diagnostico.pdf"

    generate_report(content, INTERNAL_DIAGNOSTIC, _default_config(), out_path)

    reader = PdfReader(str(out_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "USO INTERNO" in text


def test_generate_report_no_watermark_for_executive_summary(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    out_path = tmp_path / "sin_marca.pdf"

    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    reader = PdfReader(str(out_path))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "USO INTERNO" not in text


def test_generate_report_writes_atomically_no_leftover_temp_files(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    out_path = tmp_path / "atomico.pdf"

    generate_report(content, EXECUTIVE_SUMMARY, _default_config(), out_path)

    remaining = list(tmp_path.iterdir())
    assert remaining == [out_path]


def test_generate_report_raises_config_error_when_template_has_no_sections(tmp_path: Path) -> None:
    result, load_units_by_id = make_full_result()
    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )
    empty_template = ReportTemplate(key="empty", display_name="Vacío", sections=())

    with pytest.raises(PdfConfigError):
        generate_report(content, empty_template, _default_config(), tmp_path / "no_deberia.pdf")

    assert not (tmp_path / "no_deberia.pdf").exists()
