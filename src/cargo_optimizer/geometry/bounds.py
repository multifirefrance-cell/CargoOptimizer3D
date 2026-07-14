"""Validación de que una caja cabe dentro de los límites de un Loading Space."""

from __future__ import annotations

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.exceptions import OutOfBoundsError


def fits_inside_loading_space(box: AxisAlignedBox, loading_space: LoadingSpace) -> bool:
    """True si `box` cabe dentro de los límites internos del Loading Space, con tolerancia."""
    dims = loading_space.internal_dimensions
    return (
        box.min_x >= -GEOMETRY_EPSILON_CM
        and box.min_y >= -GEOMETRY_EPSILON_CM
        and box.min_z >= -GEOMETRY_EPSILON_CM
        and box.max_x <= dims.length_cm + GEOMETRY_EPSILON_CM
        and box.max_y <= dims.width_cm + GEOMETRY_EPSILON_CM
        and box.max_z <= dims.height_cm + GEOMETRY_EPSILON_CM
    )


def validate_box_inside_loading_space(box: AxisAlignedBox, loading_space: LoadingSpace) -> None:
    """Como `fits_inside_loading_space`, pero lanza `OutOfBoundsError` si no cabe."""
    if fits_inside_loading_space(box, loading_space):
        return
    dims = loading_space.internal_dimensions
    raise OutOfBoundsError(
        f"La caja X=[{box.min_x:.3f}, {box.max_x:.3f}] "
        f"Y=[{box.min_y:.3f}, {box.max_y:.3f}] Z=[{box.min_z:.3f}, {box.max_z:.3f}] "
        f"no cabe dentro del Loading Space '{loading_space.name}' "
        f"({dims.length_cm} x {dims.width_cm} x {dims.height_cm} cm)."
    )
