"""Configuración de aspecto de un informe PDF: empresa, cliente, idioma, colores, marca de agua.

Datos puros (`dataclass`), sin ningún import de `reportlab` — ver
`docs/PdfReportDesign.md`, sección 2, y ADR-0012. `presentation/desktop`
puede construir y validar esta configuración sin que `reportlab` esté
siquiera instalado en ese contexto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

_DEFAULT_ACCENT_COLOR_HEX = "#1F3864"
_DEFAULT_FOOTER_TEXT = "{company} — Página {page} de {pages} — Generado el {date}"


class ReportSection(StrEnum):
    """Los bloques de contenido reutilizables que puede incluir un informe (`sections.py`)."""

    COVER = "cover"
    EXECUTIVE_SUMMARY = "executive_summary"
    VIEWER_IMAGE = "viewer_image"
    SPACE_DETAILS = "space_details"
    PACKED_TABLE = "packed_table"
    UNPACKED_TABLE = "unpacked_table"
    WARNINGS = "warnings"
    TECHNICAL_APPENDIX = "technical_appendix"
    LEGAL_FOOTER = "legal_footer"


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Datos de la empresa que genera el informe: config. de la aplicación, no de un proyecto."""

    name: str
    logo_path: Path | None = None
    address: str = ""
    tax_id: str = ""
    contact: str = ""
    accent_color_hex: str = _DEFAULT_ACCENT_COLOR_HEX

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("CompanyProfile.name no puede estar vacío.")


@dataclass(frozen=True, slots=True)
class ClientInfo:
    """Datos del cliente para el que se genera un informe concreto. Efímero, no persistido."""

    name: str = ""
    logo_path: Path | None = None
    contact: str = ""
    reference: str = ""


@dataclass(frozen=True, slots=True)
class ReportConfig:
    """Configuración de aspecto compartida por cualquier tipo de informe.

    ``accent_color_hex`` es ``None`` por defecto (usa el de
    ``company``); un cliente con marca propia puede sobrescribirlo sin
    tocar el perfil de empresa. Los tres campos ``show_*`` controlan el
    nivel de detalle de las secciones compartidas (sección 4 de
    `docs/PdfReportDesign.md`) — los `ReportTemplate` oficiales los
    ajustan vía ``config_overrides`` (`templates.py`), nunca se editan
    aquí directamente por tipo de informe.
    """

    company: CompanyProfile
    client: ClientInfo = field(default_factory=ClientInfo)
    locale: str = "es"
    accent_color_hex: str | None = None
    header_logo_position: str = "left"
    footer_text: str = _DEFAULT_FOOTER_TEXT
    watermark_text: str | None = None
    show_position_columns: bool = True
    show_unpacked_details: bool = True
    show_algorithm_details: bool = True

    @property
    def resolved_accent_color_hex(self) -> str:
        return self.accent_color_hex or self.company.accent_color_hex
