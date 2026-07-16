"""`generate_report`: el único módulo de `infrastructure/pdf` que importa `reportlab.platypus`.

Arma el documento recorriendo `template.sections`, despachando cada
sección a su función de `sections.py`, y usa `layout.py` como
*page callback* (`canvasmaker`) para cabecera/pie/numeración/marca de
agua. Escritura siempre atómica (archivo temporal en el mismo
directorio + `os.replace`) — mismo patrón que
`save_workbook_atomic`/`ProjectFileRepository.save`.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import StyleSheet1
from reportlab.platypus import Flowable, SimpleDocTemplate

from cargo_optimizer.infrastructure.pdf.exceptions import PdfConfigError, PdfRenderError
from cargo_optimizer.infrastructure.pdf.layout import make_canvas_factory
from cargo_optimizer.infrastructure.pdf.report_config import ReportConfig, ReportSection
from cargo_optimizer.infrastructure.pdf.report_content import ReportContent
from cargo_optimizer.infrastructure.pdf.sections import (
    build_cover_section,
    build_executive_summary_section,
    build_legal_footer_section,
    build_packed_table_section,
    build_space_details_section,
    build_technical_appendix_section,
    build_unpacked_table_section,
    build_viewer_image_section,
    build_warnings_section,
)
from cargo_optimizer.infrastructure.pdf.styles import build_stylesheet, page_margin_points
from cargo_optimizer.infrastructure.pdf.templates import ReportTemplate

_SectionBuilder = Callable[[ReportContent, ReportConfig, StyleSheet1], list[Flowable]]

_SECTION_BUILDERS: dict[ReportSection, _SectionBuilder] = {
    ReportSection.EXECUTIVE_SUMMARY: build_executive_summary_section,
    ReportSection.VIEWER_IMAGE: build_viewer_image_section,
    ReportSection.SPACE_DETAILS: build_space_details_section,
    ReportSection.PACKED_TABLE: build_packed_table_section,
    ReportSection.UNPACKED_TABLE: build_unpacked_table_section,
    ReportSection.WARNINGS: build_warnings_section,
    ReportSection.TECHNICAL_APPENDIX: build_technical_appendix_section,
    ReportSection.LEGAL_FOOTER: build_legal_footer_section,
}


def _build_story(
    content: ReportContent, template: ReportTemplate, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = []
    for section in template.sections:
        if section is ReportSection.COVER:
            story.extend(
                build_cover_section(content, config, stylesheet, report_title=template.display_name)
            )
            continue
        builder = _SECTION_BUILDERS.get(section)
        if builder is not None:
            story.extend(builder(content, config, stylesheet))
    return story


def generate_report(
    content: ReportContent,
    template: ReportTemplate,
    config: ReportConfig,
    path: Path,
) -> None:
    """Genera el PDF de ``template`` con ``content``/``config`` en ``path``.

    Lanza `PdfConfigError` si la plantilla no produce ningún contenido
    (nunca ocurre con los cinco informes oficiales) y `PdfRenderError`
    ante cualquier fallo de `reportlab` o de escritura de archivo.
    """
    if not template.sections:
        raise PdfConfigError(f"La plantilla '{template.key}' no incluye ninguna sección.")

    effective_config = template.config_overrides(config)
    stylesheet = build_stylesheet(effective_config.resolved_accent_color_hex)
    story = _build_story(content, template, effective_config, stylesheet)
    if not story:
        raise PdfConfigError(f"La plantilla '{template.key}' no generó ningún contenido.")

    margin = page_margin_points()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".pdf.tmp", dir=str(path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        doc = SimpleDocTemplate(
            str(tmp_path),
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            title=content.project_name,
        )
        doc.build(story, canvasmaker=make_canvas_factory(effective_config, content))
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise PdfRenderError(f"No se pudo generar el informe PDF: {exc}") from exc
    os.replace(tmp_path, path)
