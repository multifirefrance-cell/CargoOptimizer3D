"""Rectangle2D y área de unión de rectángulos 2D.

Necesario para calcular el área de soporte de una caja sin contar dos
veces las zonas en las que dos o más cajas inferiores se solapan bajo
ella. No se añade ninguna dependencia externa (p. ej. Shapely): el
algoritmo de compresión de coordenadas usado aquí es correcto,
legible y suficientemente eficiente para las decenas o cientos de
rectángulos que puede haber bajo una caja en un layout real.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.exceptions import GeometryValidationError


@dataclass(frozen=True, slots=True)
class Rectangle2D:
    """Un rectángulo alineado con los ejes en un plano 2D (p. ej. el plano X-Y)."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        if self.max_x < self.min_x - GEOMETRY_EPSILON_CM:
            raise GeometryValidationError("max_x no puede ser menor que min_x en un Rectangle2D.")
        if self.max_y < self.min_y - GEOMETRY_EPSILON_CM:
            raise GeometryValidationError("max_y no puede ser menor que min_y en un Rectangle2D.")

    @property
    def area_cm2(self) -> float:
        return max(0.0, self.max_x - self.min_x) * max(0.0, self.max_y - self.min_y)

    def intersection(self, other: Rectangle2D) -> Rectangle2D | None:
        min_x = max(self.min_x, other.min_x)
        min_y = max(self.min_y, other.min_y)
        max_x = min(self.max_x, other.max_x)
        max_y = min(self.max_y, other.max_y)
        if max_x <= min_x + GEOMETRY_EPSILON_CM or max_y <= min_y + GEOMETRY_EPSILON_CM:
            return None
        return Rectangle2D(min_x, min_y, max_x, max_y)


def _merged_interval_length(intervals: list[tuple[float, float]]) -> float:
    """Longitud total de la unión de intervalos 1D (ya solapados fusionados)."""
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    total = 0.0
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end + GEOMETRY_EPSILON_CM:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    total += current_end - current_start
    return total


def union_area_cm2(rectangles: Sequence[Rectangle2D]) -> float:
    """Área de la unión de los rectángulos, sin doble conteo de solapes.

    Algoritmo de compresión de coordenadas en X: se ordenan todas las
    coordenadas X distintas de los rectángulos; para cada franja
    vertical entre dos coordenadas X consecutivas se calcula la unión
    1D de los intervalos Y de los rectángulos que cubren esa franja, y
    se multiplica por el ancho de la franja. La suma de todas las
    franjas es el área de la unión, determinista y sin contar dos
    veces ninguna zona.
    """
    rects = [r for r in rectangles if r.area_cm2 > GEOMETRY_EPSILON_CM]
    if not rects:
        return 0.0

    xs = sorted({r.min_x for r in rects} | {r.max_x for r in rects})
    total_area = 0.0
    for left, right in pairwise(xs):
        strip_width = right - left
        if strip_width <= GEOMETRY_EPSILON_CM:
            continue
        mid_x = (left + right) / 2.0
        y_intervals = [(r.min_y, r.max_y) for r in rects if r.min_x <= mid_x <= r.max_x]
        total_area += strip_width * _merged_interval_length(y_intervals)
    return total_area
