"""Soporte físico rectangular básico.

Conceptos: una caja en z = 0 está soportada por el suelo. Una caja
sobre otras está soportada cuando su base horizontal se superpone con
la cara superior de una o más cajas inferiores, aproximadamente a la
misma altura (con tolerancia). Esta fase no considera todavía centro
de gravedad ni vuelco: eso pertenece a una fase futura del motor de
restricciones/optimización.
"""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.exceptions import GeometryValidationError
from cargo_optimizer.geometry.rectangles import Rectangle2D, union_area_cm2


def horizontal_overlap_area_cm2(upper: AxisAlignedBox, lower: AxisAlignedBox) -> float:
    """Área en la que la base horizontal de `upper` se solapa con la de `lower`.

    No comprueba a qué altura está cada caja: solo la proyección en el
    plano X-Y. Quien llama decide si la altura es relevante (ver
    `support_area_cm2`, que sí la comprueba).
    """
    min_x = max(upper.min_x, lower.min_x)
    max_x = min(upper.max_x, lower.max_x)
    min_y = max(upper.min_y, lower.min_y)
    max_y = min(upper.max_y, lower.max_y)
    width = max_x - min_x
    depth = max_y - min_y
    if width <= GEOMETRY_EPSILON_CM or depth <= GEOMETRY_EPSILON_CM:
        return 0.0
    return width * depth


def _is_at_same_height(candidate: AxisAlignedBox, lower: AxisAlignedBox) -> bool:
    return abs(candidate.min_z - lower.max_z) <= GEOMETRY_EPSILON_CM


def support_area_cm2(candidate: AxisAlignedBox, placed_boxes: Sequence[AxisAlignedBox]) -> float:
    """Área de la base de `candidate` que está físicamente apoyada.

    Una caja apoyada en el suelo (`min_z` ≈ 0) cuenta con toda su base
    como soporte. En otro caso, se consideran solo las cajas ya
    colocadas cuya cara superior está a la misma altura que la base de
    `candidate`, y el área de soporte es la unión (sin doble conteo) de
    los solapes horizontales con cada una de ellas.
    """
    if candidate.min_z <= GEOMETRY_EPSILON_CM:
        return (candidate.max_x - candidate.min_x) * (candidate.max_y - candidate.min_y)

    rectangles: list[Rectangle2D] = []
    for lower in placed_boxes:
        if not _is_at_same_height(candidate, lower):
            continue
        min_x = max(candidate.min_x, lower.min_x)
        max_x = min(candidate.max_x, lower.max_x)
        min_y = max(candidate.min_y, lower.min_y)
        max_y = min(candidate.max_y, lower.max_y)
        if max_x <= min_x + GEOMETRY_EPSILON_CM or max_y <= min_y + GEOMETRY_EPSILON_CM:
            continue
        rectangles.append(Rectangle2D(min_x, min_y, max_x, max_y))

    return union_area_cm2(rectangles)


def support_ratio(candidate: AxisAlignedBox, placed_boxes: Sequence[AxisAlignedBox]) -> float:
    """Fracción (0.0 a 1.0) de la base de `candidate` que está apoyada."""
    base_area = (candidate.max_x - candidate.min_x) * (candidate.max_y - candidate.min_y)
    if base_area <= GEOMETRY_EPSILON_CM:
        return 0.0
    ratio = support_area_cm2(candidate, placed_boxes) / base_area
    return min(ratio, 1.0)


def is_supported(
    candidate: AxisAlignedBox,
    placed_boxes: Sequence[AxisAlignedBox],
    minimum_support_ratio: float = 1.0,
) -> bool:
    """True si `support_ratio(candidate, placed_boxes) >= minimum_support_ratio`.

    `minimum_support_ratio` debe estar en [0, 1]. El valor por defecto
    (1.0) exige soporte completo, la postura más conservadora para esta
    primera versión del motor.
    """
    if not 0.0 <= minimum_support_ratio <= 1.0:
        raise GeometryValidationError("minimum_support_ratio debe estar entre 0 y 1.")
    return support_ratio(candidate, placed_boxes) >= minimum_support_ratio - GEOMETRY_EPSILON_CM
