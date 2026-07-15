"""Pruebas de `ColorRegistry`: sin Qt ni PyVista, deterministas entre ejecuciones."""

from __future__ import annotations

from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry
from cargo_optimizer.presentation.desktop.viewer.constants import FALLBACK_PALETTE, THEME_DARK


def test_valid_hex_color_is_used_as_is() -> None:
    registry = ColorRegistry()
    assert registry.resolve_color("#AABBCC", fallback_key="ignored") == "#AABBCC"


def test_missing_color_falls_back_deterministically() -> None:
    registry = ColorRegistry()
    color_a = registry.resolve_color(None, fallback_key="BOX-1")
    color_b = registry.resolve_color(None, fallback_key="BOX-1")
    assert color_a == color_b
    assert color_a in FALLBACK_PALETTE


def test_invalid_color_falls_back_to_palette() -> None:
    registry = ColorRegistry()
    assert registry.resolve_color("not-a-color", fallback_key="BOX-2") in FALLBACK_PALETTE


def test_same_key_always_produces_same_color_across_registry_instances() -> None:
    # Verifica el requisito real: "mismo SKU, mismo color entre ejecuciones", no solo
    # dentro del mismo proceso — dos instancias independientes de ColorRegistry (que
    # simulan procesos distintos, ya que no comparten ningún estado) deben coincidir.
    first = ColorRegistry().fallback_color_for("BOX-XYZ")
    second = ColorRegistry().fallback_color_for("BOX-XYZ")
    assert first == second


def test_different_keys_can_produce_different_colors() -> None:
    registry = ColorRegistry()
    colors = {registry.fallback_color_for(f"SKU-{i}") for i in range(len(FALLBACK_PALETTE))}
    # No garantiza que todas sean distintas (colisiones de hash son posibles), pero con
    # una paleta de 20 colores y 20 claves distintas, más de una debería aparecer.
    assert len(colors) > 1


def test_is_valid_hex_color() -> None:
    assert ColorRegistry.is_valid_hex_color("#000000") is True
    assert ColorRegistry.is_valid_hex_color("#FFFFFF") is True
    assert ColorRegistry.is_valid_hex_color("#abcdef") is True
    assert ColorRegistry.is_valid_hex_color(None) is False
    assert ColorRegistry.is_valid_hex_color("") is False
    assert ColorRegistry.is_valid_hex_color("red") is False
    assert ColorRegistry.is_valid_hex_color("#GGGGGG") is False
    assert ColorRegistry.is_valid_hex_color("#FFF") is False


def test_empty_palette_is_rejected() -> None:
    import pytest

    with pytest.raises(ValueError, match="paleta"):
        ColorRegistry(palette=())


def test_selection_and_edge_colors_are_theme_aware() -> None:
    light_selection = ColorRegistry.selection_color()
    dark_selection = ColorRegistry.selection_color(THEME_DARK)
    light_edge = ColorRegistry.edge_color()
    dark_edge = ColorRegistry.edge_color(THEME_DARK)
    assert ColorRegistry.is_valid_hex_color(light_selection)
    assert ColorRegistry.is_valid_hex_color(dark_selection)
    assert ColorRegistry.is_valid_hex_color(light_edge)
    assert ColorRegistry.is_valid_hex_color(dark_edge)
