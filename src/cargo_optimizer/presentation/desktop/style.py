"""Estilo visual de la aplicación: aspecto industrial, colores neutros.

Dos temas completos (claro y oscuro) desde el principio, no solo el
claro con la promesa de un oscuro futuro: `docs/Roadmap.md` pide la
interfaz "preparada para Dark Mode", y la forma más honesta de cumplir
eso es que el modo oscuro ya funcione, seleccionable desde el menú Ver
(`MainWindow`), no que quede como una intención documentada sin código.
Ninguna paleta usa colores saturados: ambas son neutras (grises con un
único acento azul-gris discreto), apropiado para una herramienta
industrial de uso prolongado.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEME_LIGHT = "light"
THEME_DARK = "dark"

_ACCENT = QColor("#3D6E8C")


def _light_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F2F2F2"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#EAEAEA"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFDC"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#E4E4E4"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#202020"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#B00020"))
    palette.setColor(QPalette.ColorRole.Highlight, _ACCENT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8A8A8A"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#A0A0A0"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#A0A0A0"))
    return palette


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#2B2B2B"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#232323"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2F2F2F"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3A3A3A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3A3A3A"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF6B6B"))
    palette.setColor(QPalette.ColorRole.Highlight, _ACCENT)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#7A7A7A"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#6A6A6A"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#6A6A6A"))
    return palette


_QSS = """
QMainWindow::separator {
    width: 4px;
    height: 4px;
}
QToolBar {
    spacing: 4px;
    padding: 3px;
}
QStatusBar {
    padding: 2px 6px;
}
QDockWidget::title {
    padding: 4px 6px;
    font-weight: 600;
}
QHeaderView::section {
    padding: 4px 6px;
    font-weight: 600;
}
QTreeView, QTableView {
    alternate-row-colors: true;
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


__all__ = ["THEME_DARK", "THEME_LIGHT", "apply_theme", "other_theme"]
