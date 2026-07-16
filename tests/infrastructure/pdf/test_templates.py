"""Pruebas de `templates.py`: los cinco informes oficiales y sus `config_overrides`."""

from __future__ import annotations

from cargo_optimizer.infrastructure.pdf.report_config import (
    CompanyProfile,
    ReportConfig,
    ReportSection,
)
from cargo_optimizer.infrastructure.pdf.templates import (
    BUILTIN_TEMPLATES,
    CLIENT_REPORT,
    EXECUTIVE_SUMMARY,
    INTERNAL_DIAGNOSTIC,
    PACKING_LIST,
    TECHNICAL_FULL,
    get_template_by_key,
)


def test_builtin_templates_has_exactly_five_official_reports() -> None:
    assert len(BUILTIN_TEMPLATES) == 5
    assert BUILTIN_TEMPLATES == (
        EXECUTIVE_SUMMARY,
        TECHNICAL_FULL,
        PACKING_LIST,
        INTERNAL_DIAGNOSTIC,
        CLIENT_REPORT,
    )


def test_all_builtin_templates_are_marked_as_builtin_and_start_with_cover() -> None:
    for template in BUILTIN_TEMPLATES:
        assert template.is_builtin is True
        assert template.sections[0] is ReportSection.COVER


def test_get_template_by_key_finds_official_templates() -> None:
    assert get_template_by_key("executive_summary") is EXECUTIVE_SUMMARY
    assert get_template_by_key("client_report") is CLIENT_REPORT


def test_get_template_by_key_returns_none_for_unknown_key() -> None:
    assert get_template_by_key("no_existe") is None


def test_internal_diagnostic_forces_watermark() -> None:
    config = ReportConfig(company=CompanyProfile(name="Empresa"))

    effective = INTERNAL_DIAGNOSTIC.config_overrides(config)

    assert effective.watermark_text == "USO INTERNO — NO DISTRIBUIR"


def test_executive_summary_does_not_force_watermark() -> None:
    config = ReportConfig(company=CompanyProfile(name="Empresa"))

    effective = EXECUTIVE_SUMMARY.config_overrides(config)

    assert effective.watermark_text is None


def test_client_report_hides_technical_details() -> None:
    config = ReportConfig(company=CompanyProfile(name="Empresa"))

    effective = CLIENT_REPORT.config_overrides(config)

    assert effective.show_position_columns is False
    assert effective.show_algorithm_details is False
    assert effective.show_unpacked_details is False


def test_packing_list_only_has_cover_and_packed_table() -> None:
    assert PACKING_LIST.sections == (ReportSection.COVER, ReportSection.PACKED_TABLE)


def test_technical_full_includes_technical_appendix() -> None:
    assert ReportSection.TECHNICAL_APPENDIX in TECHNICAL_FULL.sections


def test_client_report_includes_legal_footer_but_not_technical_appendix() -> None:
    assert ReportSection.LEGAL_FOOTER in CLIENT_REPORT.sections
    assert ReportSection.TECHNICAL_APPENDIX not in CLIENT_REPORT.sections
