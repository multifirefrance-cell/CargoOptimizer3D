"""Sugerencia automática de color pastel para un SKU nuevo (fase OPT-17).

Deliberadamente distinto de `viewer/color_registry.py::FALLBACK_PALETTE`:
esa paleta es de alto contraste, pensada para distinguir cajas en el
visor 3D cuando no hay ningún `LoadUnit` que consultar (repuesto de
emergencia). Este módulo, en cambio, genera un color suave/pastel para
proponerlo como valor inicial de un producto de catálogo **nuevo**
(nunca configurado todavía) — un uso completamente distinto, con su
propio rango de saturación/brillo.

Determinista y sin `random`: los tonos candidatos se generan recorriendo
el círculo de matiz (HSV) con el ángulo áureo (137.507764°), que
distribuye puntos de forma uniforme y sin patrones repetitivos aunque se
generen muchos. Se elige, entre esos candidatos, el matiz que maximiza
la distancia circular mínima a los matices de `existing_colors` — así,
mientras haya matices libres, un SKU nuevo nunca queda cerca de uno ya
usado. Saturación y brillo se fijan en un rango pastel fijo (nunca
oscuro ni fluorescente): `_PASTEL_SATURATION`/`_PASTEL_VALUE`.
"""

from __future__ import annotations

import colorsys
import re
from collections.abc import Sequence

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

_PASTEL_SATURATION = 0.38
_PASTEL_VALUE = 0.92
_GOLDEN_ANGLE_DEG = 137.507764
_CANDIDATE_COUNT = 360


def suggest_pastel_color(existing_colors: Sequence[str] = ()) -> str:
    """Propone un color pastel hex, de matiz lo más distinto posible de `existing_colors`.

    `existing_colors` son los `color_hex` de los productos ya existentes
    (catálogo o proyecto, según quien llame) — cualquier valor que no
    sea un hexadecimal válido se ignora silenciosamente (no rompe la
    sugerencia). Sin colores existentes, siempre devuelve el mismo
    primer color determinista.
    """
    existing_hues = [_hue_of(color) for color in existing_colors if _HEX_COLOR_PATTERN.match(color)]

    best_hue = 0.0
    best_min_distance = -1.0
    for index in range(_CANDIDATE_COUNT):
        hue = (index * _GOLDEN_ANGLE_DEG) % 360.0
        if not existing_hues:
            best_hue = hue
            break
        distance = min(_hue_distance(hue, other) for other in existing_hues)
        if distance > best_min_distance:
            best_min_distance = distance
            best_hue = hue

    red, green, blue = colorsys.hsv_to_rgb(best_hue / 360.0, _PASTEL_SATURATION, _PASTEL_VALUE)
    return f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"


def _hue_of(color_hex: str) -> float:
    red = int(color_hex[1:3], 16) / 255.0
    green = int(color_hex[3:5], 16) / 255.0
    blue = int(color_hex[5:7], 16) / 255.0
    hue, _saturation, _value = colorsys.rgb_to_hsv(red, green, blue)
    return hue * 360.0


def _hue_distance(first_deg: float, second_deg: float) -> float:
    diff = abs(first_deg - second_deg) % 360.0
    return min(diff, 360.0 - diff)
