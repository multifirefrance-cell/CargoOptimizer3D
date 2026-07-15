"""`ColorRegistry`: color por SKU, determinista entre ejecuciones del programa.

`LoadUnit.color_hex` es la fuente primaria (el dominio ya lo valida:
`^#[0-9A-Fa-f]{6}$`, con `"#CCCCCC"` por defecto — casi siempre hay un
valor válido). `ColorRegistry` solo entra en juego para el color de
repuesto: cuando no hay `LoadUnit` que consultar (referencia
desconocida, ver `scene_builder.py`) o, defensivamente, si el valor
recibido no es un hexadecimal válido.

**Nunca usar `hash()` de Python sobre cadenas para esto**: desde
Python 3.3 el hash de `str` está aleatorizado por proceso
(`PYTHONHASHSEED`) por seguridad — "mismo SKU, mismo color" se
rompería entre dos ejecuciones del programa aunque el código nunca use
`random`. Se usa `zlib.crc32` (estable entre procesos e
implementaciones de Python) para indexar una paleta curada de alto
contraste (`viewer/constants.py::FALLBACK_PALETTE`), nunca RGB
aleatorio directo del hash.
"""

from __future__ import annotations

import re
import zlib
from collections.abc import Sequence

from cargo_optimizer.presentation.desktop.viewer.constants import (
    FALLBACK_PALETTE,
    THEME_LIGHT,
    theme_colors,
)

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ColorRegistry:
    """Resuelve el color de una caja, y los colores de tema (selección, bordes)."""

    def __init__(self, palette: Sequence[str] = FALLBACK_PALETTE) -> None:
        if not palette:
            raise ValueError("La paleta de repuesto no puede estar vacía.")
        self._palette = tuple(palette)

    @staticmethod
    def is_valid_hex_color(value: str | None) -> bool:
        return value is not None and bool(_HEX_COLOR_PATTERN.match(value))

    def resolve_color(self, color_hex: str | None, fallback_key: str) -> str:
        """`color_hex` si es válido; si no, un color determinista derivado de `fallback_key`."""
        if self.is_valid_hex_color(color_hex):
            assert color_hex is not None  # narrowing para mypy; ya lo comprueba is_valid_hex_color
            return color_hex
        return self.fallback_color_for(fallback_key)

    def fallback_color_for(self, key: str) -> str:
        """Color determinista para `key` (mismo `key` -> mismo color, entre ejecuciones)."""
        index = zlib.crc32(key.encode("utf-8")) % len(self._palette)
        return self._palette[index]

    @staticmethod
    def selection_color(theme: str = THEME_LIGHT) -> str:
        return theme_colors(theme)["selection"]

    @staticmethod
    def edge_color(theme: str = THEME_LIGHT) -> str:
        return theme_colors(theme)["edge"]
