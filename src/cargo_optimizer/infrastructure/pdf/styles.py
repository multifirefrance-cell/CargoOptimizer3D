"""Tipografía, colores y estilos de tabla compartidos por todos los informes PDF.

Centralizado aquí para que ningún tipo de informe reimplemente su
propio formato ad-hoc — mismo papel que `infrastructure/excel/styles.py`
cumple para las hojas de cálculo (fase 8.0). Fuentes estándar de PDF
(Helvetica), sin fuentes embebidas: suficiente para un documento de
texto/tablas, sin el coste de empaquetar tipografías propias.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import TableStyle

PAGE_MARGIN_CM = 2.0
FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

_MUTED_TEXT_COLOR = colors.HexColor("#595959")
_TABLE_HEADER_TEXT_COLOR = colors.white
_TABLE_ROW_ALT_COLOR = colors.HexColor("#F2F2F2")
_TABLE_GRID_COLOR = colors.HexColor("#B0B0B0")

WATERMARK_COLOR = colors.HexColor("#C00000")
WATERMARK_FONT_SIZE = 60
WATERMARK_OPACITY = 0.15


def accent_color(accent_color_hex: str) -> Color:
    """Convierte un `#RRGGBB` de `ReportConfig` a un `reportlab.lib.colors.Color`."""
    return colors.HexColor(accent_color_hex)


def build_stylesheet(accent_color_hex: str) -> StyleSheet1:
    """Hoja de estilos de párrafo para un informe, con el color de acento ya aplicado."""
    stylesheet = getSampleStyleSheet()
    accent = accent_color(accent_color_hex)

    stylesheet.add(
        ParagraphStyle(
            name="ReportTitle",
            fontName=FONT_BOLD,
            fontSize=20,
            leading=24,
            textColor=accent,
            spaceAfter=6,
        )
    )
    stylesheet.add(
        ParagraphStyle(
            name="ReportSubtitle",
            fontName=FONT_BODY,
            fontSize=13,
            leading=16,
            textColor=_MUTED_TEXT_COLOR,
            spaceAfter=12,
        )
    )
    stylesheet.add(
        ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=accent,
            spaceBefore=14,
            spaceAfter=6,
        )
    )
    stylesheet.add(
        ParagraphStyle(
            name="ReportBody",
            fontName=FONT_BODY,
            fontSize=10,
            leading=13,
        )
    )
    stylesheet.add(
        ParagraphStyle(
            name="ReportMuted",
            fontName=FONT_ITALIC,
            fontSize=9,
            leading=12,
            textColor=_MUTED_TEXT_COLOR,
        )
    )
    stylesheet.add(
        ParagraphStyle(
            name="FooterText",
            fontName=FONT_BODY,
            fontSize=8,
            leading=10,
            textColor=_MUTED_TEXT_COLOR,
        )
    )
    return stylesheet


def table_style(accent_color_hex: str) -> TableStyle:
    """Estilo de tabla compartido: cabecera con el color de acento, franjas de fila suaves."""
    accent = accent_color(accent_color_hex)
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), accent),
            ("TEXTCOLOR", (0, 0), (-1, 0), _TABLE_HEADER_TEXT_COLOR),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), FONT_BODY),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _TABLE_ROW_ALT_COLOR]),
            ("GRID", (0, 0), (-1, -1), 0.5, _TABLE_GRID_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def page_margin_points() -> float:
    return PAGE_MARGIN_CM * cm
