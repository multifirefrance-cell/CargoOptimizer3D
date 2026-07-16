"""Pruebas de `report_content.py`: traducción de `PackingResult` a `ReportContent`."""

from __future__ import annotations

from cargo_optimizer.infrastructure.pdf.report_content import build_report_content
from tests.infrastructure.pdf._helpers import make_empty_result, make_full_result


def test_build_report_content_resolves_sku_and_name() -> None:
    result, load_units_by_id = make_full_result()

    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )

    assert len(content.packed_rows) == 1
    assert content.packed_rows[0].sku == "SKU-1"
    assert content.packed_rows[0].name == "Caja de prueba"
    assert len(content.unpacked_rows) == 1
    assert content.unpacked_rows[0].reason_code == "OUT_OF_BOUNDS"


def test_build_report_content_unknown_unit_uses_placeholder() -> None:
    result, _load_units_by_id = make_full_result()

    content = build_report_content(result, {}, project_name="Proyecto", application_version="9.9.9")

    assert content.packed_rows[0].name == "(producto desconocido)"


def test_build_report_content_sorts_packed_rows_by_sequence_number() -> None:
    result, load_units_by_id = make_full_result()

    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )

    sequence_numbers = [row.sequence_number for row in content.packed_rows]
    assert sequence_numbers == sorted(sequence_numbers)


def test_build_report_content_weight_utilization_none_when_no_limit() -> None:
    empty_result, load_units_by_id = make_empty_result()

    content = build_report_content(
        empty_result, load_units_by_id, project_name="Vacío", application_version="9.9.9"
    )

    assert content.weight_utilization_percent is None
    assert content.space_max_weight_kg is None


def test_build_report_content_empty_project_has_no_rows() -> None:
    empty_result, load_units_by_id = make_empty_result()

    content = build_report_content(
        empty_result, load_units_by_id, project_name="Vacío", application_version="9.9.9"
    )

    assert content.packed_rows == ()
    assert content.unpacked_rows == ()
    assert content.warnings == ()
    assert content.requested_count == 0


def test_build_report_content_carries_viewer_screenshot() -> None:
    result, load_units_by_id = make_full_result()
    png_bytes = b"\x89PNG\r\n\x1a\n"

    content = build_report_content(
        result,
        load_units_by_id,
        project_name="Proyecto",
        application_version="9.9.9",
        viewer_screenshot_png=png_bytes,
    )

    assert content.viewer_screenshot_png == png_bytes


def test_build_report_content_defaults_viewer_screenshot_to_none() -> None:
    result, load_units_by_id = make_full_result()

    content = build_report_content(
        result, load_units_by_id, project_name="Proyecto", application_version="9.9.9"
    )

    assert content.viewer_screenshot_png is None
