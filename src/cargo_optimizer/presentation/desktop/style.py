"""Estilo visual de la aplicación: aspecto comercial moderno, no industrial-gris.

Dos temas completos (claro y oscuro) desde el principio, no solo el
claro con la promesa de un oscuro futuro: `docs/Roadmap.md` pide la
interfaz "preparada para Dark Mode", y la forma más honesta de cumplir
eso es que el modo oscuro ya funcione, seleccionable desde el menú Ver
(`MainWindow`), no que quede como una intención documentada sin código.

Paleta con un acento moderno más una paleta semántica reducida (éxito/
advertencia/error/información) — nunca color saturado en superficies
grandes, siempre reservado a estados puntuales (KPI, avisos, iconos de
estado), para que siga siendo apta para uso industrial prolongado sin
fatiga visual. Los cuatro colores semánticos y la escala de espaciado
se exponen como constantes (`SUCCESS`/`WARNING`/`ERROR`/`INFO`/
`SPACING_*`) para que los paneles los reutilicen en vez de definir sus
propios valores sueltos.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEME_LIGHT = "light"
THEME_DARK = "dark"

_ACCENT = QColor("#2F6FED")
_ACCENT_DARK_MODE = QColor("#5B8DEF")

# Colores semánticos: mismo significado en ambos temas, ajustados en
# saturación/luminosidad para mantener contraste legible sobre cada
# fondo. Usar siempre estas constantes en vez de un `QColor("#...")`
# suelto en un panel — un único punto de verdad para "verde de éxito".
SUCCESS_LIGHT = QColor("#1E8E3E")
SUCCESS_DARK = QColor("#5FBF77")
WARNING_LIGHT = QColor("#B15C00")
WARNING_DARK = QColor("#F2A93B")
ERROR_LIGHT = QColor("#C62828")
ERROR_DARK = QColor("#F26B6B")
INFO_LIGHT = QColor("#0B72B9")
INFO_DARK = QColor("#5AB8F2")

# Escala de espaciado: múltiplos de una unidad base de 4px. Usar estos
# valores en vez de números sueltos en `setContentsMargins`/`setSpacing`
# para que la interfaz "respire" de forma consistente.
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 20
SPACING_XL = 32


def semantic_colors(theme: str) -> dict[str, QColor]:
    """Colores de éxito/advertencia/error/información para el tema dado."""
    if theme == THEME_DARK:
        return {
            "success": SUCCESS_DARK,
            "warning": WARNING_DARK,
            "error": ERROR_DARK,
            "info": INFO_DARK,
        }
    return {
        "success": SUCCESS_LIGHT,
        "warning": WARNING_LIGHT,
        "error": ERROR_LIGHT,
        "info": INFO_LIGHT,
    }


def _light_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F5F6F8"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1A1D21"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F0F2F5"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1A1D21"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1A1D21"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#EDEFF2"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1A1D21"))
    palette.setColor(QPalette.ColorRole.BrightText, ERROR_LIGHT)
    palette.setColor(QPalette.ColorRole.Highlight, _ACCENT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8A8F98"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#A6ABB3"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#A6ABB3"))
    return palette


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1E2126"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E6E8EB"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#26292F"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2E323A"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#33373F"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E6E8EB"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#E6E8EB"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#33373F"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E6E8EB"))
    palette.setColor(QPalette.ColorRole.BrightText, ERROR_DARK)
    palette.setColor(QPalette.ColorRole.Highlight, _ACCENT_DARK_MODE)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0E1013"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#7B818B"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#5B616B"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#5B616B"))
    return palette


_QSS = """
* {
    font-size: 10.5pt;
}
QMainWindow::separator {
    width: 5px;
    height: 5px;
}
QToolBar {
    spacing: 8px;
    padding: 6px 8px;
    border: none;
}
QToolButton {
    padding: 6px 10px;
    border-radius: 6px;
}
QToolButton:hover {
    background: rgba(127, 127, 127, 0.15);
}
QPushButton {
    padding: 6px 14px;
    border-radius: 6px;
}
QStatusBar {
    padding: 3px 8px;
}
QDockWidget::title {
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11pt;
}
QHeaderView::section {
    padding: 6px 8px;
    font-weight: 600;
}
QTreeView, QTableView, QListWidget {
    alternate-row-colors: true;
}
QTabBar::tab {
    padding: 8px 16px;
}
QGroupBox {
    font-weight: 600;
    margin-top: 12px;
}
"""


def apply_theme(app: QApplication, theme: str) -> None:
    """Aplica el tema `THEME_LIGHT` o `THEME_DARK` a toda la aplicación."""
    app.setStyle("Fusion")
    palette = _dark_palette() if theme == THEME_DARK else _light_palette()
    app.setPalette(palette)
    app.setStyleSheet(_QSS)


def other_theme(theme: str) -> str:
    """El tema contrario al dado — útil para construir la acción de alternar tema."""
    return THEME_LIGHT if theme == THEME_DARK else THEME_DARK


__all__ = [
    "ERROR_DARK",
    "ERROR_LIGHT",
    "INFO_DARK",
    "INFO_LIGHT",
    "SPACING_LG",
    "SPACING_MD",
    "SPACING_SM",
    "SPACING_XL",
    "SPACING_XS",
    "SUCCESS_DARK",
    "SUCCESS_LIGHT",
    "THEME_DARK",
    "THEME_LIGHT",
    "WARNING_DARK",
    "WARNING_LIGHT",
    "apply_theme",
    "other_theme",
    "semantic_colors",
]
