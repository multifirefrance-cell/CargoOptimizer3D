"""Cabecera, pie de página, numeración y marca de agua — comunes a cualquier informe.

Callback de página transversal (sección 2 de `docs/PdfReportDesign.md`):
aislado en su propio módulo para probarlo una vez (numeración correcta
con 1 página, con muchas; marca de agua solo cuando se configura) sin
repetirlo por cada tipo de informe. La numeración "Página X de Y" exige
conocer el total de páginas antes de dibujarlo, así que el `Canvas` se
sustituye por una variante que guarda el estado de cada página y solo
dibuja cabecera/pie/marca de agua en una segunda pasada, al llamar a
`save()` — es la técnica estándar de ReportLab para "Página X de Y".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from cargo_optimizer.infrastructure.pdf.report_config import ReportConfig
from cargo_optimizer.infrastructure.pdf.report_content import ReportContent
from cargo_optimizer.infrastructure.pdf.styles import (
    FONT_BODY,
    WATERMARK_COLOR,
    WATERMARK_FONT_SIZE,
    WATERMARK_OPACITY,
)

_LOGO_MAX_WIDTH_CM = 3.5
_LOGO_MAX_HEIGHT_CM = 1.5
_HEADER_MARGIN_CM = 1.2
_FOOTER_Y_CM = 1.2


def _page_width_cm(pdf_canvas: canvas.Canvas) -> float:
    return float(pdf_canvas._pagesize[0]) / cm  # type: ignore[attr-defined]


def _page_height_cm(pdf_canvas: canvas.Canvas) -> float:
    return float(pdf_canvas._pagesize[1]) / cm  # type: ignore[attr-defined]


def _logo_x_cm(position: str, page_width_cm: float) -> float:
    if position == "right":
        return page_width_cm - _LOGO_MAX_WIDTH_CM - 2.0
    if position == "center":
        return (page_width_cm - _LOGO_MAX_WIDTH_CM) / 2.0
    return 2.0


def _draw_logo(
    pdf_canvas: canvas.Canvas, logo_path: Path | None, *, x_cm: float, top_y_cm: float
) -> None:
    """Dibuja el logo con su borde superior en ``top_y_cm``; nunca lanza ni bloquea el PDF.

    ``logo_path is None`` (sin logo) y una ruta que no existe o no es
    una imagen legible se tratan exactamente igual: la cabecera se
    dibuja sin logo, nunca produce un error.
    """
    if logo_path is None:
        return
    try:
        if not logo_path.is_file():
            return
        image = ImageReader(str(logo_path))
        width, height = image.getSize()
        scale = min(_LOGO_MAX_WIDTH_CM * cm / width, _LOGO_MAX_HEIGHT_CM * cm / height, 1.0)
        draw_width = width * scale
        draw_height = height * scale
        pdf_canvas.drawImage(
            image,
            x_cm * cm,
            top_y_cm * cm - draw_height,
            width=draw_width,
            height=draw_height,
            mask="auto",
            preserveAspectRatio=True,
        )
    except Exception:  # noqa: BLE001 - un logo ilegible nunca debe romper la generación del PDF
        return


def _draw_header(pdf_canvas: canvas.Canvas, config: ReportConfig) -> None:
    page_width_cm = _page_width_cm(pdf_canvas)
    page_height_cm = _page_height_cm(pdf_canvas)
    x_cm = _logo_x_cm(config.header_logo_position, page_width_cm)
    _draw_logo(
        pdf_canvas,
        config.company.logo_path,
        x_cm=x_cm,
        top_y_cm=page_height_cm - _HEADER_MARGIN_CM,
    )


def _format_footer_text(config: ReportConfig, content: ReportContent, page: int, pages: int) -> str:
    return config.footer_text.format(
        company=config.company.name,
        date=content.generated_at.strftime("%Y-%m-%d"),
        page=page,
        pages=pages,
    )


def _draw_footer(
    pdf_canvas: canvas.Canvas,
    config: ReportConfig,
    content: ReportContent,
    *,
    page: int,
    pages: int,
) -> None:
    text = _format_footer_text(config, content, page, pages)
    pdf_canvas.saveState()
    pdf_canvas.setFont(FONT_BODY, 8)
    pdf_canvas.setFillColorRGB(0.35, 0.35, 0.35)
    pdf_canvas.drawCentredString(_page_width_cm(pdf_canvas) / 2.0 * cm, _FOOTER_Y_CM * cm, text)
    pdf_canvas.restoreState()


def _draw_watermark(pdf_canvas: canvas.Canvas, watermark_text: str) -> None:
    pdf_canvas.saveState()
    pdf_canvas.setFont(FONT_BODY, WATERMARK_FONT_SIZE)
    pdf_canvas.setFillColor(WATERMARK_COLOR, alpha=WATERMARK_OPACITY)
    width_cm = _page_width_cm(pdf_canvas)
    height_cm = _page_height_cm(pdf_canvas)
    pdf_canvas.translate(width_cm / 2.0 * cm, height_cm / 2.0 * cm)
    pdf_canvas.rotate(45)
    pdf_canvas.drawCentredString(0, 0, watermark_text)
    pdf_canvas.restoreState()


def make_canvas_factory(config: ReportConfig, content: ReportContent) -> type[canvas.Canvas]:
    """Construye la clase de `Canvas` a pasar como ``canvasmaker`` a `SimpleDocTemplate.build`.

    Cierra sobre ``config``/``content`` para poder dibujar cabecera, pie,
    numeración y marca de agua sin que `report_builder.py` tenga que
    conocer los detalles de dibujo.
    """

    class _ReportCanvas(canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_page_states: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 - nombre exigido por la API de reportlab
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()  # type: ignore[attr-defined]

        def save(self) -> None:
            total_pages = len(self._saved_page_states)
            for index, state in enumerate(self._saved_page_states, start=1):
                self.__dict__.update(state)
                _draw_header(self, config)
                _draw_footer(self, config, content, page=index, pages=total_pages)
                if config.watermark_text:
                    _draw_watermark(self, config.watermark_text)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

    return _ReportCanvas
