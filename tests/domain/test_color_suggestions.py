"""Pruebas de `color_suggestions.py`: color pastel automático para un SKU nuevo (fase OPT-17)."""

from __future__ import annotations

import colorsys

from cargo_optimizer.domain.color_suggestions import (
    _HEX_COLOR_PATTERN,
    _PASTEL_SATURATION,
    _PASTEL_VALUE,
    suggest_pastel_color,
)


def _assert_is_pastel(color_hex: str) -> None:
    assert _HEX_COLOR_PATTERN.match(color_hex)
    red = int(color_hex[1:3], 16) / 255.0
    green = int(color_hex[3:5], 16) / 255.0
    blue = int(color_hex[5:7], 16) / 255.0
    _hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    # Tolerancia de redondeo hex <-> HSV, nunca oscuro ni fluorescente/saturado.
    assert abs(saturation - _PASTEL_SATURATION) < 0.02
    assert abs(value - _PASTEL_VALUE) < 0.02


def test_first_color_with_no_existing_colors_is_deterministic() -> None:
    first = suggest_pastel_color(())
    second = suggest_pastel_color(())
    assert first == second
    _assert_is_pastel(first)


def test_is_deterministic_for_the_same_existing_colors() -> None:
    existing = ("#F5B7B1", "#A9DFBF")
    first = suggest_pastel_color(existing)
    second = suggest_pastel_color(existing)
    assert first == second


def test_never_dark_or_highly_saturated() -> None:
    for existing in ((), ("#112233",), ("#FF00FF", "#00FF00", "#0000FF")):
        _assert_is_pastel(suggest_pastel_color(existing))


def test_prefers_a_hue_far_from_existing_colors() -> None:
    # Un único color existente de matiz ~0 grados (rojo): el nuevo debe
    # alejarse, nunca coincidir con ese mismo matiz.
    existing_red = "#FF0000"
    suggested = suggest_pastel_color((existing_red,))

    def hue_of(color_hex: str) -> float:
        red = int(color_hex[1:3], 16) / 255.0
        green = int(color_hex[3:5], 16) / 255.0
        blue = int(color_hex[5:7], 16) / 255.0
        hue, _s, _v = colorsys.rgb_to_hsv(red, green, blue)
        return hue * 360.0

    existing_hue = hue_of(existing_red)
    suggested_hue = hue_of(suggested)
    diff = abs(existing_hue - suggested_hue) % 360.0
    circular_distance = min(diff, 360.0 - diff)
    assert circular_distance > 60.0


def test_distinct_colors_across_several_new_skus() -> None:
    """Fase OPT-17: mientras haya matices libres, SKU nuevos sucesivos no deben repetirse."""
    colors: list[str] = []
    for _ in range(6):
        colors.append(suggest_pastel_color(colors))
    assert len(set(colors)) == len(colors)


def test_ignores_invalid_or_blank_entries_in_existing_colors() -> None:
    valid_only = suggest_pastel_color(("#AABBCC",))
    with_garbage = suggest_pastel_color(("#AABBCC", "", "not-a-color", "#ZZZZZZ"))
    assert valid_only == with_garbage
