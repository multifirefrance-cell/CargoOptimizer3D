"""Configuración visual centralizada del visor 3D.

Ningún color ni opacidad del visor se define fuera de este módulo (ver
`docs/ThreeDViewerDesign.md`, sección 17: "no dispersar colores en
múltiples archivos"). `scene_controller.py` y `color_registry.py`
importan de aquí, nunca escriben un literal de color propio.
"""

from __future__ import annotations

# Paleta curada de alto contraste para ColorRegistry cuando un LoadUnit
# es desconocido o no declara color_hex válido. Elegida a mano (no
# generada), pensada para distinguirse tanto sobre fondo claro como
# oscuro. El orden importa: es el orden de asignación por índice de hash.
FALLBACK_PALETTE: tuple[str, ...] = (
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#EECA3B",
    "#B279A2",
    "#FF9DA6",
    "#9D755D",
    "#BAB0AC",
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
)

# Opacidades (0.0 - 1.0). Las cajas son siempre sólidas: la
# transparencia es del LoadingSpace, para no ocultar las cajas.
WALL_OPACITY = 0.12
FLOOR_OPACITY = 0.25
BOX_OPACITY = 1.0

# Grosores de línea (unidades de PyVista/VTK, aprox. píxeles de pantalla).
WIREFRAME_LINE_WIDTH = 1.5
BOX_EDGE_LINE_WIDTH = 1.0
DOOR_HIGHLIGHT_LINE_WIDTH = 4.0
SELECTION_LINE_WIDTH = 3.0

THEME_LIGHT = "light"
THEME_DARK = "dark"

# Colores por tema. Coherentes con `presentation/desktop/style.py`
# (mismo `_ACCENT` para selección, mismo espíritu de paleta neutra).
_ACCENT = "#3D6E8C"

THEME_COLORS: dict[str, dict[str, str]] = {
    THEME_LIGHT: {
        "background": "#F2F2F2",
        "wall": "#8A8A8A",
        "floor": "#B5B5B5",
        "edge": "#404040",
        "axis_x": "#B00020",
        "axis_y": "#1B5E20",
        "axis_z": "#0D47A1",
        "selection": _ACCENT,
        "door_highlight": _ACCENT,
        "text": "#202020",
        "fallback_background": "#F2F2F2",
    },
    THEME_DARK: {
        "background": "#2B2B2B",
        "wall": "#9A9A9A",
        "floor": "#6E6E6E",
        "edge": "#D0D0D0",
        "axis_x": "#FF6B6B",
        "axis_y": "#66BB6A",
        "axis_z": "#64B5F6",
        "selection": _ACCENT,
        "door_highlight": _ACCENT,
        "text": "#E0E0E0",
        "fallback_background": "#2B2B2B",
    },
}


def theme_colors(theme: str) -> dict[str, str]:
    """Colores del tema dado; cae a `THEME_LIGHT` si `theme` no se reconoce."""
    return THEME_COLORS.get(theme, THEME_COLORS[THEME_LIGHT])
