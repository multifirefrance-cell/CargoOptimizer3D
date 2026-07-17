"""Genera `packaging/app_icon.ico` (multi-resolución) con Pillow, sin dependencias nuevas.

No es parte del paquete `cargo_optimizer` (no toca `src/`): es una
utilidad de empaquetado, ejecutada una sola vez para producir el icono
del `.exe`/instalador. El diseño es deliberadamente simple —una caja
isométrica en el color de acento de la interfaz (`#2F6FED`, ver
`presentation/desktop/style.py`)— no un logotipo definitivo de marca.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

_ACCENT = (47, 111, 237)  # #2F6FED, mismo acento que style.py
_ACCENT_DARK = (30, 78, 176)
_ACCENT_LIGHT = (109, 154, 245)
_OUTPUT_PATH = Path(__file__).parent / "app_icon.ico"
_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _draw_box(size: int) -> Image.Image:
    """Una caja isométrica simple centrada en un lienzo cuadrado transparente."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = size * 0.08
    width = size - 2 * margin
    top_h = width * 0.42
    front_h = width * 0.5

    cx = size / 2.0
    top_y = margin
    mid_y = top_y + top_h
    bottom_y = mid_y + front_h

    left_x = cx - width / 2.0
    right_x = cx + width / 2.0

    # Cara superior (rombo).
    draw.polygon(
        [(cx, top_y), (right_x, top_y + top_h / 2.0), (cx, mid_y), (left_x, top_y + top_h / 2.0)],
        fill=(*_ACCENT_LIGHT, 255),
    )
    # Cara frontal izquierda.
    left_mid_y = mid_y + front_h / 2.0
    draw.polygon(
        [(left_x, top_y + top_h / 2.0), (cx, mid_y), (cx, bottom_y), (left_x, left_mid_y)],
        fill=(*_ACCENT, 255),
    )
    # Cara frontal derecha.
    right_mid_y = mid_y + front_h / 2.0
    draw.polygon(
        [(right_x, top_y + top_h / 2.0), (cx, mid_y), (cx, bottom_y), (right_x, right_mid_y)],
        fill=(*_ACCENT_DARK, 255),
    )
    return image


def main() -> None:
    base = _draw_box(256)
    images = [base.resize((s, s), Image.LANCZOS) if s != 256 else base for s in _SIZES]
    base.save(_OUTPUT_PATH, format="ICO", sizes=[(s, s) for s in _SIZES], append_images=images[1:])
    print(f"Generado: {_OUTPUT_PATH} ({_OUTPUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
