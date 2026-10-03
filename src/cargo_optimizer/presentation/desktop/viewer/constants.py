"""Configuración visual centralizada del visor 3D.

Ningún color ni opacidad del visor se define fuera de este módulo (ver
`docs/ThreeDViewerDesign.md`, sección 17: "no dispersar colores en
múltiples archivos"). `scene_controller.py` y `color_registry.py`
importan de aquí, nunca escriben un literal de color propio.
"""

from __future__ import annotations

from cargo_optimizer.presentation.desktop.style import THEME_DARK, THEME_LIGHT

# Paleta curada de alto contraste para ColorRegistry cuando un LoadUnit
# es desconocido o no declara color_hex válido. Elegida a mano (no
# generada), pensada para distinguirse tanto sobre fondo claro como
# oscuro. El orden importa: es el orden de asignación por índice de hash.
FALLBACK_PALETTE: tuple[str, ...] = (
    "#E53935",  # rojo vivo
    "#FB8C00",  # naranja
    "#FDD835",  # amarillo
    "#43A047",  # verde
    "#1E88E5",  # azul
    "#8E24AA",  # violeta
    "#00ACC1",  # cyan
    "#F06292",  # rosa
    "#FF7043",  # naranja oscuro
    "#26A69A",  # teal
    "#C0CA33",  # lima
    "#AB47BC",  # lila
    "#5C6BC0",  # índigo
    "#EC407A",  # fucsia
    "#66BB6A",  # verde claro
    "#42A5F5",  # azul claro
    "#FFCA28",  # ámbar
    "#EF5350",  # rojo claro
    "#26C6DA",  # cyan claro
    "#D4E157",  # lima claro
)

# Opacidades (0.0 - 1.0). Las cajas son siempre sólidas: la
# transparencia es del LoadingSpace, para no ocultar las cajas.
WALL_OPACITY = 0.08   # paredes muy tenues — solo insinuadas, como en EasyCargo
FLOOR_OPACITY = 0.35  # piso más visible para dar sensación de superficie
BOX_OPACITY = 1.0

# Grosores de línea (unidades de PyVista/VTK, aprox. píxeles de pantalla).
WIREFRAME_LINE_WIDTH = 2.0  # borde del contenedor más definido
BOX_EDGE_LINE_WIDTH = 1.5
DOOR_HIGHLIGHT_LINE_WIDTH = 4.0
SELECTION_LINE_WIDTH = 3.0

# Colores por tema. Coherentes con `presentation/desktop/style.py`
# (mismo `_ACCENT` para selección — rojo Induprox).
_ACCENT = "#D32F2F"

THEME_COLORS: dict[str, dict[str, str]] = {
    THEME_LIGHT: {
        "background": "#ECEEF2",  # ligeramente azulado-gris: más neutro que gris puro
        "wall": "#9AACBA",        # azul-gris suave: distinguible del fondo sin saturar
        "floor": "#C8CDD6",       # gris claro azulado: sensación de superficie limpia
        "edge": "#3A4A5A",        # azul oscuro: borde del contenedor bien definido
        "axis_x": "#C62828",
        "axis_y": "#2E7D32",
        "axis_z": "#1565C0",
        "selection": _ACCENT,
        "door_highlight": _ACCENT,
        "text": "#202020",
        "fallback_background": "#ECEEF2",
    },
    THEME_DARK: {
        "background": "#252830",  # azul-oscuro: más rico que gris neutro
        "wall": "#7A8B99",
        "floor": "#5A6470",
        "edge": "#C8D0DA",
        "axis_x": "#FF6B6B",
        "axis_y": "#66BB6A",
        "axis_z": "#64B5F6",
        "selection": _ACCENT,
        "door_highlight": _ACCENT,
        "text": "#E0E0E0",
        "fallback_background": "#252830",
    },
}


def theme_colors(theme: str) -> dict[str, str]:
    """Colores del tema dado; cae a `THEME_LIGHT` si `theme` no se reconoce."""
    return THEME_COLORS.get(theme, THEME_COLORS[THEME_LIGHT])
