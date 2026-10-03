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

# Valor centinela que `LoadUnit` asigna por defecto cuando no se ha elegido color:
# se trata como "sin color configurado" y se sustituye por la paleta de respaldo.
_DEFAULT_NO_COLOR = "#cccccc"


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
        """`color_hex` si es válido y no es el gris por defecto; si no, paleta por `fallback_key`."""
        if self.is_valid_hex_color(color_hex) and color_hex.lower() != _DEFAULT_NO_COLOR:  # type: ignore[union-attr]
            return color_hex  # type: ignore[return-value]
        return self.fallback_color_for(fallback_key)

    def fallback_color_for(self, key: str) -> str:
        """Color determinista para `key` (mismo `key` -> mismo color, entre ejecuciones)."""
        index = zlib.crc32(key.encode("utf-8")) % len(self._palette)
        return self._palette[index]

    def assign_unique_palette_colors(
        self, sku_color_map: dict[str, str | None]
    ) -> dict[str, str]:
        """Asigna un color único a cada SKU, garantizando que no haya colisiones.

        SKUs con `color_hex` explícito y válido (distinto del gris centinela) se
        respetan tal cual. Los demás reciben el color de la paleta de repuesto
        empezando desde su índice preferido (crc32 % N) y avanzando si ese slot
        ya está ocupado. El orden de procesamiento es alfabético para que la
        asignación sea estable entre ejecuciones aunque varíe el número de SKUs.
        """
        result: dict[str, str] = {}
        used_lowers: set[str] = set()

        # 1ª pasada: colores explícitos
        for sku, color in sku_color_map.items():
            if self.is_valid_hex_color(color) and color.lower() != _DEFAULT_NO_COLOR:  # type: ignore[union-attr]
                result[sku] = color  # type: ignore[assignment]
                used_lowers.add(color.lower())

        # 2ª pasada: paleta sin colisión para los que no tienen color explícito
        for sku in sorted(sku for sku in sku_color_map if sku not in result):
            preferred = zlib.crc32(sku.encode("utf-8")) % len(self._palette)
            for offset in range(len(self._palette)):
                candidate = self._palette[(preferred + offset) % len(self._palette)]
                if candidate.lower() not in used_lowers:
                    result[sku] = candidate
                    used_lowers.add(candidate.lower())
                    break
            else:
                # Paleta agotada (más SKUs que colores): reutiliza el preferido
                result[sku] = self._palette[preferred]

        return result

    @staticmethod
    def selection_color(theme: str = THEME_LIGHT) -> str:
        return theme_colors(theme)["selection"]

    @staticmethod
    def edge_color(theme: str = THEME_LIGHT) -> str:
        return theme_colors(theme)["edge"]
