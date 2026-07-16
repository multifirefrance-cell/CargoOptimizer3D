"""Bloques de contenido reutilizables de un informe (`ReportSection`, `report_config.py`).

Cada función recibe `ReportContent` + `ReportConfig` (y la hoja de
estilos ya construida) y devuelve una lista de *flowables* de
`reportlab`. Los cinco tipos de informe (`templates.py`) son,
literalmente, una selección y un orden distintos de estas mismas
funciones — ver `docs/PdfReportDesign.md`, sección 2.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.styles import StyleSheet1
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, Image, PageBreak, Paragraph, Spacer, Table

from cargo_optimizer.infrastructure.pdf.report_config import ReportConfig
from cargo_optimizer.infrastructure.pdf.report_content import ReportContent
from cargo_optimizer.infrastructure.pdf.styles import table_style

_CONTENT_WIDTH_CM = 17.0
_NO_WEIGHT_LIMIT_LABEL = "Sin límite declarado"


def _safe_image(path: Path | None, *, max_width_cm: float, max_height_cm: float) -> Image | None:
    """Un `Image` de tamaño acotado si ``path`` existe y es legible; `None` en cualquier otro caso.

    Nunca lanza: un logo ausente o corrupto no debe impedir generar el
    resto del informe (mismo criterio que la captura del visor 3D).
    """
    if path is None:
        return None
    try:
        if not path.is_file():
            return None
        image = Image(str(path))
        scale = min(
            max_width_cm * cm / image.imageWidth, max_height_cm * cm / image.imageHeight, 1.0
        )
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
        return image
    except Exception:  # noqa: BLE001 - un logo ilegible nunca debe romper la generación del PDF
        return None


def _label_value_table(
    rows: list[tuple[str, str]], stylesheet: StyleSheet1, accent_hex: str
) -> Table:
    body_style = stylesheet["ReportBody"]
    data = [
        [Paragraph(f"<b>{label}</b>", body_style), Paragraph(value, body_style)]
        for label, value in rows
    ]
    table = Table(data, colWidths=[6.0 * cm, (_CONTENT_WIDTH_CM - 6.0) * cm])
    table.setStyle(table_style(accent_hex))
    return table


def _weight_utilization_label(content: ReportContent) -> str:
    if content.weight_utilization_percent is None:
        return _NO_WEIGHT_LIMIT_LABEL
    return f"{content.weight_utilization_percent:.1f} %"


def build_cover_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1, *, report_title: str
) -> list[Flowable]:
    story: list[Flowable] = []
    logo = _safe_image(config.company.logo_path, max_width_cm=6.0, max_height_cm=3.0)
    if logo is not None:
        story.append(logo)
        story.append(Spacer(1, 18))
    story.append(Paragraph(content.project_name, stylesheet["ReportTitle"]))
    story.append(Paragraph(report_title, stylesheet["ReportSubtitle"]))
    story.append(Spacer(1, 24))

    info_rows: list[tuple[str, str]] = [("Empresa", config.company.name)]
    if config.client.name:
        info_rows.append(("Cliente", config.client.name))
        if config.client.reference:
            info_rows.append(("Referencia", config.client.reference))
    info_rows.append(("Fecha de generación", content.generated_at.strftime("%Y-%m-%d %H:%M UTC")))
    story.append(_label_value_table(info_rows, stylesheet, config.resolved_accent_color_hex))
    story.append(PageBreak())
    return story


def build_executive_summary_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = [Paragraph("Resumen ejecutivo", stylesheet["SectionHeading"])]
    rows: list[tuple[str, str]] = [
        ("Unidades solicitadas", str(content.requested_count)),
        ("Unidades cargadas", str(content.packed_count)),
        ("Unidades no cargadas", str(content.unpacked_count)),
        ("Porcentaje completado", f"{content.packing_completion_percent:.1f} %"),
        ("Volumen utilizado", f"{content.volume_utilization_percent:.1f} %"),
        ("Peso utilizado", _weight_utilization_label(content)),
    ]
    if config.show_algorithm_details:
        rows.append(("Algoritmo utilizado", content.algorithm_name))
        rows.append(("Tiempo de ejecución", f"{content.execution_time_seconds:.2f} s"))
    story.append(_label_value_table(rows, stylesheet, config.resolved_accent_color_hex))
    story.append(Spacer(1, 12))
    return story


def build_viewer_image_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    """Vacía si no hay captura del visor 3D — nunca produce un error ni un hueco visible."""
    if content.viewer_screenshot_png is None:
        return []
    try:
        image = Image(BytesIO(content.viewer_screenshot_png))
        scale = min(_CONTENT_WIDTH_CM * cm / image.imageWidth, 1.0)
        image.drawWidth = image.imageWidth * scale
        image.drawHeight = image.imageHeight * scale
    except Exception:  # noqa: BLE001 - una captura corrupta nunca debe romper el resto del informe
        return []
    return [
        Paragraph("Vista 3D del resultado", stylesheet["SectionHeading"]),
        image,
        Spacer(1, 12),
    ]


def build_space_details_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = [Paragraph("Espacio de carga", stylesheet["SectionHeading"])]
    dimensions_label = (
        f"{content.space_length_cm:g} × {content.space_width_cm:g} × {content.space_height_cm:g}"
    )
    rows: list[tuple[str, str]] = [
        ("Nombre", content.space_name),
        ("Categoría", content.space_category_label),
        ("Dimensiones internas (cm)", dimensions_label),
        (
            "Peso máximo",
            (
                _NO_WEIGHT_LIMIT_LABEL
                if content.space_max_weight_kg is None
                else f"{content.space_max_weight_kg:g} kg"
            ),
        ),
        ("Posición de puerta", content.space_door_position_label),
    ]
    if content.space_notes:
        rows.append(("Notas", content.space_notes))
    story.append(_label_value_table(rows, stylesheet, config.resolved_accent_color_hex))
    story.append(Spacer(1, 12))
    return story


def build_packed_table_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = [Paragraph("Productos cargados", stylesheet["SectionHeading"])]
    if not content.packed_rows:
        story.append(Paragraph("No hay productos cargados.", stylesheet["ReportBody"]))
        story.append(Spacer(1, 12))
        return story

    if config.show_position_columns:
        header = [
            "Orden",
            "SKU",
            "Nombre",
            "Posición (X, Y, Z cm)",
            "Orientación",
            "Dimensiones (cm)",
        ]
        rows = [header] + [
            [
                str(row.sequence_number),
                row.sku,
                row.name,
                f"{row.position_x_cm:g}, {row.position_y_cm:g}, {row.position_z_cm:g}",
                row.orientation_label,
                f"{row.length_cm:g} × {row.width_cm:g} × {row.height_cm:g}",
            ]
            for row in content.packed_rows
        ]
        col_widths = [1.5 * cm, 3.0 * cm, 4.5 * cm, 4.0 * cm, 2.5 * cm, 1.5 * cm]
    else:
        header = ["Orden", "SKU", "Nombre"]
        rows = [header] + [
            [str(row.sequence_number), row.sku, row.name] for row in content.packed_rows
        ]
        col_widths = [2.0 * cm, 5.0 * cm, 10.0 * cm]

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(table_style(config.resolved_accent_color_hex))
    story.append(table)
    story.append(Spacer(1, 12))
    return story


def build_unpacked_table_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = [Paragraph("Productos no cargados", stylesheet["SectionHeading"])]
    if not content.unpacked_rows:
        story.append(
            Paragraph(
                "Todos los productos solicitados se cargaron correctamente.",
                stylesheet["ReportBody"],
            )
        )
        story.append(Spacer(1, 12))
        return story

    if config.show_unpacked_details:
        header = ["SKU", "Nombre", "Instancia", "Motivo", "Detalle"]
        rows = [header] + [
            [row.sku, row.name, str(row.instance_number), row.reason_code, row.reason_message]
            for row in content.unpacked_rows
        ]
        col_widths = [2.5 * cm, 4.0 * cm, 1.8 * cm, 3.0 * cm, 5.7 * cm]
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(table_style(config.resolved_accent_color_hex))
        story.append(table)
    else:
        story.append(
            Paragraph(
                f"{len(content.unpacked_rows)} producto(s) no se pudieron cargar.",
                stylesheet["ReportBody"],
            )
        )
        unique_reasons = sorted({row.reason_message for row in content.unpacked_rows})
        for reason in unique_reasons:
            story.append(Paragraph(f"• {reason}", stylesheet["ReportBody"]))
    story.append(Spacer(1, 12))
    return story


def build_warnings_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    if not content.warnings:
        return []
    story: list[Flowable] = [Paragraph("Avisos", stylesheet["SectionHeading"])]
    for warning in content.warnings:
        story.append(Paragraph(f"• {warning}", stylesheet["ReportBody"]))
    story.append(Spacer(1, 12))
    return story


def build_technical_appendix_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    story: list[Flowable] = [Paragraph("Apéndice técnico", stylesheet["SectionHeading"])]
    rows: list[tuple[str, str]] = [
        ("Algoritmo utilizado", content.algorithm_name),
        ("Tiempo de ejecución", f"{content.execution_time_seconds:.3f} s"),
        ("Versión de CargoOptimizer3D", content.application_version),
    ]
    story.append(_label_value_table(rows, stylesheet, config.resolved_accent_color_hex))
    story.append(Spacer(1, 12))
    return story


def build_legal_footer_section(
    content: ReportContent, config: ReportConfig, stylesheet: StyleSheet1
) -> list[Flowable]:
    return [
        Spacer(1, 18),
        Paragraph(
            "Este documento ha sido generado automáticamente por CargoOptimizer3D a partir de "
            "un cálculo de optimización de carga. Las cifras reflejan el resultado del algoritmo "
            "en la fecha de generación indicada.",
            stylesheet["ReportMuted"],
        ),
    ]
