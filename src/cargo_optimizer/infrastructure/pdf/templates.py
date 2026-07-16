"""`ReportTemplate` y los cinco informes oficiales, como datos (ADR-0012).

Los cinco informes (`docs/PdfReportDesign.md`, sección 3) son cinco
instancias constantes de `ReportTemplate` — nunca cinco clases o cinco
funciones `generate_*` distintas. Añadir un sexto informe en el futuro
es declarar una sexta constante, no escribir código nuevo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from cargo_optimizer.infrastructure.pdf.report_config import ReportConfig, ReportSection

_WATERMARK_INTERNAL_USE = "USO INTERNO — NO DISTRIBUIR"


def _identity(config: ReportConfig) -> ReportConfig:
    return config


def _internal_diagnostic_overrides(config: ReportConfig) -> ReportConfig:
    return replace(config, watermark_text=_WATERMARK_INTERNAL_USE)


def _client_report_overrides(config: ReportConfig) -> ReportConfig:
    return replace(
        config,
        show_position_columns=False,
        show_algorithm_details=False,
        show_unpacked_details=False,
    )


@dataclass(frozen=True, slots=True)
class ReportTemplate:
    """Qué informe generar: nombre, secciones en orden, y ajustes de configuración."""

    key: str
    display_name: str
    sections: tuple[ReportSection, ...]
    config_overrides: Callable[[ReportConfig], ReportConfig] = _identity
    is_builtin: bool = True


EXECUTIVE_SUMMARY = ReportTemplate(
    key="executive_summary",
    display_name="Resumen ejecutivo",
    sections=(
        ReportSection.COVER,
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.VIEWER_IMAGE,
        ReportSection.SPACE_DETAILS,
    ),
)

TECHNICAL_FULL = ReportTemplate(
    key="technical_full",
    display_name="Informe técnico completo",
    sections=(
        ReportSection.COVER,
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.VIEWER_IMAGE,
        ReportSection.SPACE_DETAILS,
        ReportSection.PACKED_TABLE,
        ReportSection.UNPACKED_TABLE,
        ReportSection.WARNINGS,
        ReportSection.TECHNICAL_APPENDIX,
    ),
)

PACKING_LIST = ReportTemplate(
    key="packing_list",
    display_name="Packing list optimizado",
    sections=(
        ReportSection.COVER,
        ReportSection.PACKED_TABLE,
    ),
)

INTERNAL_DIAGNOSTIC = ReportTemplate(
    key="internal_diagnostic",
    display_name="Informe interno de diagnóstico",
    sections=(
        ReportSection.COVER,
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.SPACE_DETAILS,
        ReportSection.PACKED_TABLE,
        ReportSection.UNPACKED_TABLE,
        ReportSection.WARNINGS,
        ReportSection.TECHNICAL_APPENDIX,
    ),
    config_overrides=_internal_diagnostic_overrides,
)

CLIENT_REPORT = ReportTemplate(
    key="client_report",
    display_name="Informe para cliente",
    sections=(
        ReportSection.COVER,
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.VIEWER_IMAGE,
        ReportSection.SPACE_DETAILS,
        ReportSection.PACKED_TABLE,
        ReportSection.UNPACKED_TABLE,
        ReportSection.LEGAL_FOOTER,
    ),
    config_overrides=_client_report_overrides,
)

BUILTIN_TEMPLATES: tuple[ReportTemplate, ...] = (
    EXECUTIVE_SUMMARY,
    TECHNICAL_FULL,
    PACKING_LIST,
    INTERNAL_DIAGNOSTIC,
    CLIENT_REPORT,
)


def get_template_by_key(key: str) -> ReportTemplate | None:
    """El `ReportTemplate` oficial con ese `key`, o `None` si no existe."""
    for template in BUILTIN_TEMPLATES:
        if template.key == key:
            return template
    return None
