"""Generación de informes PDF profesionales (fase 9.1).

Diseñado en la fase 9.0 (`docs/PdfReportDesign.md`, ADR-0012), depende
únicamente de `domain` y de `reportlab` — nunca de `optimization`,
`presentation`, `infrastructure/excel` ni `infrastructure/database`. Ver
`docs/PdfReports.md` para el detalle de uso.
"""

from __future__ import annotations

from cargo_optimizer.infrastructure.pdf.exceptions import PdfConfigError, PdfError, PdfRenderError
from cargo_optimizer.infrastructure.pdf.report_builder import generate_report
from cargo_optimizer.infrastructure.pdf.report_config import (
    ClientInfo,
    CompanyProfile,
    ReportConfig,
    ReportSection,
)
from cargo_optimizer.infrastructure.pdf.report_content import (
    ProductRow,
    ReportContent,
    UnpackedRow,
    build_report_content,
)
from cargo_optimizer.infrastructure.pdf.templates import (
    BUILTIN_TEMPLATES,
    CLIENT_REPORT,
    EXECUTIVE_SUMMARY,
    INTERNAL_DIAGNOSTIC,
    PACKING_LIST,
    TECHNICAL_FULL,
    ReportTemplate,
    get_template_by_key,
)

__all__ = [
    "BUILTIN_TEMPLATES",
    "CLIENT_REPORT",
    "EXECUTIVE_SUMMARY",
    "INTERNAL_DIAGNOSTIC",
    "PACKING_LIST",
    "TECHNICAL_FULL",
    "ClientInfo",
    "CompanyProfile",
    "PdfConfigError",
    "PdfError",
    "PdfRenderError",
    "ProductRow",
    "ReportConfig",
    "ReportContent",
    "ReportSection",
    "ReportTemplate",
    "UnpackedRow",
    "build_report_content",
    "generate_report",
    "get_template_by_key",
]
