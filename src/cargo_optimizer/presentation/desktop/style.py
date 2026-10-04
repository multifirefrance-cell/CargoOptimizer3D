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

_ACCENT = QColor("#D32F2F")          # Rojo Induprox
_ACCENT_DARK_MODE = QColor("#EF5350")  # Rojo claro para modo oscuro

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


def utilization_color(pct: float) -> str:
    """Color de texto para un porcentaje de utilización del espacio de carga."""
    if pct >= 85:
        return "#43A047"
    if pct >= 60:
        return "#FB8C00"
    if pct > 0:
        return "#1E88E5"
    return "#888888"


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


_QSS_LIGHT = """
* { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; }

QMainWindow { background: #F5F6F8; }
QMainWindow::separator { width: 4px; height: 4px; background: #D0D3D8; }

QToolBar {
    spacing: 6px; padding: 5px 10px; border: none;
    border-bottom: 1px solid #D0D3D8; background: #FFFFFF;
}
QToolButton {
    padding: 5px 12px; border-radius: 6px; color: #1A1D21;
    font-weight: 500;
}
QToolButton:hover  { background: #F0F2F5; }
QToolButton:pressed { background: #E2E6EC; }
QToolButton:disabled { color: #A6ABB3; }

QPushButton {
    padding: 6px 16px; border-radius: 6px;
    background: #EDEFF2; color: #1A1D21; border: none; font-weight: 500;
}
QPushButton:hover   { background: #DDE0E6; }
QPushButton:pressed { background: #CDD1D9; }
QPushButton[class="primary"] {
    background: #D32F2F; color: #FFFFFF;
}
QPushButton[class="primary"]:hover   { background: #B71C1C; }
QPushButton[class="primary"]:pressed { background: #C62828; }
QPushButton[class="compact"] { font-size: 8pt; padding: 1px 8px; }

QSplitter::handle { background: #D0D3D8; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover { background: #D32F2F; }

QStatusBar { padding: 3px 10px; border-top: 1px solid #D0D3D8; background: #FFFFFF; }

QDockWidget::title {
    padding: 8px 12px; font-weight: 600; font-size: 10.5pt;
    background: #EDEFF2; border-bottom: 1px solid #D0D3D8;
}

QGroupBox {
    font-weight: 700; margin-top: 16px; padding-top: 8px;
    border: 1px solid #D0D3D8; border-radius: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 10px; padding: 0 4px;
    color: #5A5F6A;
}

QHeaderView::section {
    padding: 6px 10px; font-weight: 700;
    background: #EDEFF2; border: none; border-right: 1px solid #D0D3D8;
    border-bottom: 1px solid #C0C4CC;
}
QHeaderView::section:first { border-left: none; }

QTableView, QTreeView, QListView {
    gridline-color: #E5E7EB; border: 1px solid #D0D3D8;
    selection-background-color: #FDECEA;
    selection-color: #1A1D21;
    alternate-background-color: #F8F9FB;
}
QTableView::item:alternate, QTreeView::item:alternate { background: #F8F9FB; }
QTableView::item:selected, QTreeView::item:selected   { background: #FDECEA; color: #1A1D21; }
QTableView::item:hover,    QTreeView::item:hover      { background: #FFF5F5; }

#productCatalogTableView { font-size: 9pt; }
#productTableView         { font-size: 9pt; }
#catalogLoadTable         { font-size: 9pt; }

QTabBar::tab {
    padding: 8px 18px; border: none; margin-right: 2px;
    border-radius: 4px 4px 0 0; font-weight: 500;
}
QTabBar::tab:selected  { background: #FFFFFF; font-weight: 700; border-bottom: 2px solid #D32F2F; }
QTabBar::tab:!selected { background: #EDEFF2; color: #5A5F6A; }
QTabBar::tab:hover     { background: #F5F6F8; }

QScrollBar:vertical   { width: 8px; background: transparent; }
QScrollBar:horizontal { height: 8px; background: transparent; }
QScrollBar::handle { background: #C0C4CC; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:hover { background: #D32F2F; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

QComboBox {
    padding: 4px 8px; border: 1px solid #D0D3D8; border-radius: 5px;
    background: #FFFFFF;
}
QComboBox:hover  { border-color: #D32F2F; }
QComboBox:focus  { border-color: #D32F2F; }
QComboBox::drop-down { border: none; width: 20px; }

QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    padding: 4px 8px; border: 1px solid #D0D3D8; border-radius: 5px;
    background: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus { border-color: #D32F2F; }

/* Pane del contenedor de pestañas */
QTabWidget::pane {
    border: 1px solid #D0D3D8;
    border-top: none;
    background: #FFFFFF;
}

QLabel[class="section-title"] { font-weight: 700; font-size: 11pt; color: #D32F2F; }
QLabel[class="kpi-value"]     { font-weight: 700; font-size: 14pt; }

/* Barra de estadísticas sobre el visor 3D */
#viewerStatsHeader {
    background: #F5F7FA;
    border-bottom: 1px solid #D0D3D8;
}

/* Panel izquierdo: espacio de carga */
#loadingSpaceSummaryPanel { background: #EDEFF2; }

/* Tarjeta de producto seleccionado */
#productCard {
    background: #FFFFFF;
    border: 1px solid #D0D3D8;
    border-radius: 6px;
}

/* Combo de búsqueda de productos: borde más visible */
#productSearchCombo { border: 1.5px solid #C0C4CC; border-radius: 6px; }
#productSearchCombo:focus { border-color: #D32F2F; }

/* Botón Agregar: extra prominencia */
#addToLoadButton { font-size: 10.5pt; }

/* Botones de vista en la barra de estadísticas del visor 3D */
#viewerStatsHeader QPushButton {
    border: 1px solid #C0C4CC;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 8pt;
    background: transparent;
}
#viewerStatsHeader QPushButton:hover   { background: #E8EBF0; border-color: #A0A4AC; }
#viewerStatsHeader QPushButton:pressed { background: #D0D3D8; }

/* Botón de acción de advertencia (destructivo reversible, p.ej. Archivar) */
QPushButton[class="warning"] {
    background: #FFF3E0; color: #B15C00; border: 1px solid #FFCC80;
}
QPushButton[class="warning"]:hover   { background: #FFE0B2; }
QPushButton[class="warning"]:pressed { background: #FFCC80; }

/* Panel de avisos: fondo ámbar sutil cuando hay contenido */
#warningsList, #multiSpaceWarningsList {
    background: #FFFDF5;
    border: 1px solid #FFE082;
    border-radius: 4px;
}

/* Barra de progreso de optimización en la barra de estado */
#optimizationProgressBar {
    border: 1px solid #C0C4CC;
    border-radius: 4px;
    background: #EDEFF2;
    text-align: center;
    font-size: 8.5pt;
}
#optimizationProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #D32F2F, stop:1 #EF5350);
    border-radius: 3px;
}

/* Tooltips */
QToolTip {
    background: #FFFFFF; color: #1A1D21;
    border: 1px solid #C0C4CC; border-radius: 4px;
    padding: 4px 8px; font-size: 9.5pt;
}

/* Label de título de KPI tile */
QLabel#kpiTileTitle {
    font-size: 8.5pt; font-weight: 600; color: #7A808A;
}

/* Tarjetas KPI: fondo sutil + hover */
QFrame#kpiTile {
    background: #F5F7FA;
    border: 1px solid #E0E3E8;
    border-radius: 6px;
}
QFrame#kpiTile:hover {
    background: #EDF0F5;
    border-color: #C0C4CC;
}

/* Panel de registro: fondo tipo editor, fuente monoespaciada más pequeña */
#logText {
    background: #F8F9FB;
    border: 1px solid #D0D3D8;
    border-radius: 4px;
    font-size: 8.5pt;
}

/* Diálogos: fondo coherente con el tema */
QDialog { background: #F5F6F8; }

/* CheckBox */
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid #C0C4CC; border-radius: 3px;
    background: #FFFFFF;
}
QCheckBox::indicator:hover  { border-color: #D32F2F; }
QCheckBox::indicator:checked {
    background: #D32F2F; border-color: #D32F2F;
}
QCheckBox::indicator:disabled { background: #E8EAED; border-color: #D0D3D8; }

/* Hover en cabeceras de tabla */
QHeaderView::section:hover { background: #E2E4E8; }

/* Corner widget del scroll area (esquina inferior-derecha) */
QAbstractScrollArea::corner { background: #EDEFF2; border: none; }

/* Separadores de sección en formularios */
QFrame#formSectionSep {
    border: none; border-top: 1px solid #E0E3E8; margin: 2px 0;
}

/* Etiquetas de sección (encabezados de grupo dentro de un panel) */
QLabel[class="sectionLabel"] {
    font-size: 8.5pt;
    font-weight: 700;
    color: #7A808A;
    padding-bottom: 2px;
    border-bottom: 1px solid #D0D3D8;
}

/* Texto secundario/muted (subtítulos, dimensiones, etc.) */
QLabel[class="mutedLabel"] { font-size: 9pt; color: #888888; }
"""

_QSS_DARK = """
* { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; }

QMainWindow { background: #1E2126; }
QMainWindow::separator { width: 4px; height: 4px; background: #3A3F47; }

QToolBar {
    spacing: 6px; padding: 5px 10px; border: none;
    border-bottom: 1px solid #3A3F47; background: #26292F;
}
QToolButton {
    padding: 5px 12px; border-radius: 6px; color: #E6E8EB; font-weight: 500;
}
QToolButton:hover   { background: rgba(255,255,255,0.08); }
QToolButton:pressed { background: rgba(255,255,255,0.12); }
QToolButton:disabled { color: #5B616B; }

QPushButton {
    padding: 6px 16px; border-radius: 6px;
    background: #33373F; color: #E6E8EB; border: none; font-weight: 500;
}
QPushButton:hover   { background: #3E4450; }
QPushButton:pressed { background: #484E5C; }
QPushButton[class="primary"] { background: #EF5350; color: #FFFFFF; }
QPushButton[class="primary"]:hover   { background: #E53935; }
QPushButton[class="primary"]:pressed { background: #C62828; }
QPushButton[class="compact"] { font-size: 8pt; padding: 1px 8px; }

QSplitter::handle { background: #3A3F47; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover { background: #EF5350; }

QStatusBar { padding: 3px 10px; border-top: 1px solid #3A3F47; background: #26292F; }

QDockWidget::title {
    padding: 8px 12px; font-weight: 600; font-size: 10.5pt;
    background: #2E323A; border-bottom: 1px solid #3A3F47;
}

QGroupBox {
    font-weight: 700; margin-top: 16px; padding-top: 8px;
    border: 1px solid #3A3F47; border-radius: 6px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 10px; padding: 0 4px;
    color: #9AA0AA;
}

QHeaderView::section {
    padding: 6px 10px; font-weight: 700;
    background: #2E323A; color: #E6E8EB;
    border: none; border-right: 1px solid #3A3F47; border-bottom: 1px solid #3A3F47;
}

QTableView, QTreeView, QListView {
    gridline-color: #3A3F47; border: 1px solid #3A3F47;
    selection-background-color: #4A2020;
    selection-color: #E6E8EB;
    alternate-background-color: #2E323A;
}
QTableView::item:alternate, QTreeView::item:alternate { background: #2E323A; }
QTableView::item:selected, QTreeView::item:selected   { background: #4A2020; }
QTableView::item:hover,    QTreeView::item:hover      { background: #3A2525; }

#productCatalogTableView { font-size: 9pt; }
#productTableView         { font-size: 9pt; }
#catalogLoadTable         { font-size: 9pt; }

QTabBar::tab {
    padding: 8px 18px; border: none; margin-right: 2px;
    border-radius: 4px 4px 0 0; font-weight: 500; color: #9AA0AA;
}
QTabBar::tab:selected  { background: #26292F; color: #E6E8EB; font-weight: 700; border-bottom: 2px solid #EF5350; }
QTabBar::tab:!selected { background: #2E323A; }
QTabBar::tab:hover     { background: #33373F; color: #E6E8EB; }

QScrollBar:vertical   { width: 8px; background: transparent; }
QScrollBar:horizontal { height: 8px; background: transparent; }
QScrollBar::handle { background: #4A4F5A; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:hover { background: #EF5350; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

QComboBox {
    padding: 4px 8px; border: 1px solid #3A3F47; border-radius: 5px;
    background: #33373F; color: #E6E8EB;
}
QComboBox:hover { border-color: #EF5350; }
QComboBox:focus { border-color: #EF5350; }
QComboBox::drop-down { border: none; width: 20px; }

QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    padding: 4px 8px; border: 1px solid #3A3F47; border-radius: 5px;
    background: #33373F; color: #E6E8EB;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus { border-color: #EF5350; }

/* Pane del contenedor de pestañas */
QTabWidget::pane {
    border: 1px solid #3A3F47;
    border-top: none;
    background: #26292F;
}

QLabel[class="section-title"] { font-weight: 700; font-size: 11pt; color: #EF5350; }
QLabel[class="kpi-value"]     { font-weight: 700; font-size: 14pt; }

/* Barra de estadísticas sobre el visor 3D */
#viewerStatsHeader {
    background: #1E2028;
    border-bottom: 1px solid #3A3F47;
}

/* Panel izquierdo: espacio de carga */
#loadingSpaceSummaryPanel { background: #26292F; }

/* Tarjeta de producto seleccionado */
#productCard {
    background: #33373F;
    border: 1px solid #3A3F47;
    border-radius: 6px;
}

/* Combo de búsqueda */
#productSearchCombo { border: 1.5px solid #4A4F5A; border-radius: 6px; }
#productSearchCombo:focus { border-color: #EF5350; }

/* Botón Agregar */
#addToLoadButton { font-size: 10.5pt; }

/* Botones de vista en la barra de estadísticas del visor 3D */
#viewerStatsHeader QPushButton {
    border: 1px solid #3A3F47;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 8pt;
    background: transparent;
    color: #D0D0D0;
}
#viewerStatsHeader QPushButton:hover   { background: #33373F; border-color: #55595F; }
#viewerStatsHeader QPushButton:pressed { background: #26292F; }

/* Botón de acción de advertencia (destructivo reversible) */
QPushButton[class="warning"] {
    background: #2C1F0A; color: #F2A93B; border: 1px solid #5A3D00;
}
QPushButton[class="warning"]:hover   { background: #3A2910; }
QPushButton[class="warning"]:pressed { background: #4A3515; }

/* Panel de avisos: fondo ámbar oscuro muy sutil */
#warningsList, #multiSpaceWarningsList {
    background: #252015;
    border: 1px solid #5A4500;
    border-radius: 4px;
}

/* Barra de progreso de optimización */
#optimizationProgressBar {
    border: 1px solid #3A3F47;
    border-radius: 4px;
    background: #2E323A;
    text-align: center;
    font-size: 8.5pt;
    color: #E6E8EB;
}
#optimizationProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #EF5350, stop:1 #F57F7F);
    border-radius: 3px;
}

/* Tooltips */
QToolTip {
    background: #2E323A; color: #E6E8EB;
    border: 1px solid #4A4F5A; border-radius: 4px;
    padding: 4px 8px; font-size: 9.5pt;
}

/* Label de título de KPI tile */
QLabel#kpiTileTitle {
    font-size: 8.5pt; font-weight: 600; color: #9AA0AA;
}

/* Tarjetas KPI: fondo sutil + hover */
QFrame#kpiTile {
    background: #23272E;
    border: 1px solid #343840;
    border-radius: 6px;
}
QFrame#kpiTile:hover {
    background: #2A2F38;
    border-color: #4A4F5A;
}

/* Panel de registro */
#logText {
    background: #1A1D21;
    border: 1px solid #3A3F47;
    border-radius: 4px;
    font-size: 8.5pt;
    color: #C8CDD6;
}

/* Diálogos */
QDialog { background: #1E2126; }

/* CheckBox */
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid #4A4F5A; border-radius: 3px;
    background: #33373F;
}
QCheckBox::indicator:hover  { border-color: #EF5350; }
QCheckBox::indicator:checked {
    background: #EF5350; border-color: #EF5350;
}
QCheckBox::indicator:disabled { background: #2A2D33; border-color: #3A3F47; }

/* Hover en cabeceras de tabla */
QHeaderView::section:hover { background: #363B44; }

/* Corner widget */
QAbstractScrollArea::corner { background: #2E323A; border: none; }

/* Separadores de sección en formularios */
QFrame#formSectionSep {
    border: none; border-top: 1px solid #3A3F47; margin: 2px 0;
}

/* Etiquetas de sección (encabezados de grupo dentro de un panel) */
QLabel[class="sectionLabel"] {
    font-size: 8.5pt;
    font-weight: 700;
    color: #9AA0AA;
    padding-bottom: 2px;
    border-bottom: 1px solid #3A3F47;
}

/* Texto secundario/muted (subtítulos, dimensiones, etc.) */
QLabel[class="mutedLabel"] { font-size: 9pt; color: #9A9DA6; }
"""

_QSS = _QSS_LIGHT  # default; se sobreescribe en apply_theme


def apply_theme(app: QApplication, theme: str) -> None:
    """Aplica el tema `THEME_LIGHT` o `THEME_DARK` a toda la aplicación."""
    app.setStyle("Fusion")
    palette = _dark_palette() if theme == THEME_DARK else _light_palette()
    app.setPalette(palette)
    app.setStyleSheet(_QSS_DARK if theme == THEME_DARK else _QSS_LIGHT)


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
    "utilization_color",
]
