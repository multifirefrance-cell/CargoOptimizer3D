"""Pruebas de `report_config.py`: `CompanyProfile`, `ClientInfo`, `ReportConfig`."""

from __future__ import annotations

from pathlib import Path

import pytest

from cargo_optimizer.infrastructure.pdf.report_config import (
    ClientInfo,
    CompanyProfile,
    ReportConfig,
)


def test_company_profile_requires_non_empty_name() -> None:
    with pytest.raises(ValueError, match="no puede estar vacío"):
        CompanyProfile(name="   ")


def test_report_config_resolved_accent_color_falls_back_to_company() -> None:
    company = CompanyProfile(name="Empresa", accent_color_hex="#112233")
    config = ReportConfig(company=company)

    assert config.resolved_accent_color_hex == "#112233"


def test_report_config_accent_color_override_wins_over_company() -> None:
    company = CompanyProfile(name="Empresa", accent_color_hex="#112233")
    config = ReportConfig(company=company, accent_color_hex="#AABBCC")

    assert config.resolved_accent_color_hex == "#AABBCC"


def test_report_config_default_client_is_empty() -> None:
    config = ReportConfig(company=CompanyProfile(name="Empresa"))

    assert config.client == ClientInfo()
    assert config.client.name == ""


def test_report_config_defaults_show_everything() -> None:
    config = ReportConfig(company=CompanyProfile(name="Empresa"))

    assert config.show_position_columns is True
    assert config.show_unpacked_details is True
    assert config.show_algorithm_details is True
    assert config.watermark_text is None


def test_company_profile_accepts_logo_path() -> None:
    company = CompanyProfile(name="Empresa", logo_path=Path("logo.png"))

    assert company.logo_path == Path("logo.png")
