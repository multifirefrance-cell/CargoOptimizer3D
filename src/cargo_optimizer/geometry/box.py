"""AxisAlignedBox: caja ortoédrica alineada con los ejes X, Y, Z.

Sistema de coordenadas (igual que en ``domain``, ver
docs/DomainModel.md): X = largo, Y = ancho, Z = alto; origen en el
suelo, esquina trasera izquierda.
"""

from __future__ import annotations

from dataclasses import dataclass

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM


def _axis_overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
    """Longitud de solape de dos intervalos en un eje; negativa si están separados."""
    return min(a_max, b_max) - max(a_min, b_min)


@dataclass(frozen=True, slots=True)
class AxisAlignedBox:
    """Una caja ortoédrica en el espacio del Loading Space.

    ``position`` es la esquina de coordenadas mínimas
    (min_x, min_y, min_z). ``dimensions`` ya viene orientada: al igual
    que en ``Orientation``, ``length_cm`` es la extensión en X,
    ``width_cm`` en Y y ``height_cm`` en Z.
    """

    position: Position3D
    dimensions: Dimensions3D

    @property
    def min_x(self) -> float:
        return self.position.x_cm

    @property
    def min_y(self) -> float:
        return self.position.y_cm

    @property
    def min_z(self) -> float:
        return self.position.z_cm

    @property
    def max_x(self) -> float:
        return self.position.x_cm + self.dimensions.length_cm

    @property
    def max_y(self) -> float:
        return self.position.y_cm + self.dimensions.width_cm

    @property
    def max_z(self) -> float:
        return self.position.z_cm + self.dimensions.height_cm

    @property
    def volume_cm3(self) -> float:
        return self.dimensions.volume_cm3

    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2.0

    @property
    def center_z(self) -> float:
        return (self.min_z + self.max_z) / 2.0

    def contains_point(self, position: Position3D) -> bool:
        return (
            self.min_x - GEOMETRY_EPSILON_CM <= position.x_cm <= self.max_x + GEOMETRY_EPSILON_CM
            and self.min_y - GEOMETRY_EPSILON_CM
            <= position.y_cm
            <= self.max_y + GEOMETRY_EPSILON_CM
            and self.min_z - GEOMETRY_EPSILON_CM
            <= position.z_cm
            <= self.max_z + GEOMETRY_EPSILON_CM
        )

    def contains_box(self, other: AxisAlignedBox) -> bool:
        return (
            self.min_x <= other.min_x + GEOMETRY_EPSILON_CM
            and self.min_y <= other.min_y + GEOMETRY_EPSILON_CM
            and self.min_z <= other.min_z + GEOMETRY_EPSILON_CM
            and self.max_x >= other.max_x - GEOMETRY_EPSILON_CM
            and self.max_y >= other.max_y - GEOMETRY_EPSILON_CM
            and self.max_z >= other.max_z - GEOMETRY_EPSILON_CM
        )

    def intersects(self, other: AxisAlignedBox) -> bool:
        """Cualquier intersección, incluido el simple contacto (cara, arista o vértice compartidos).

        Semántica elegida: es el test AABB estándar sobre regiones
        cerradas. Devuelve ``True`` tanto si hay volumen de
        intersección positivo (ver ``overlaps``) como si las cajas
        únicamente se tocan (ver ``touches``). Solo es ``False`` cuando
        las cajas están genuinamente separadas en al menos un eje.
        """
        return (
            _axis_overlap(self.min_x, self.max_x, other.min_x, other.max_x) >= -GEOMETRY_EPSILON_CM
            and _axis_overlap(self.min_y, self.max_y, other.min_y, other.max_y)
            >= -GEOMETRY_EPSILON_CM
            and _axis_overlap(self.min_z, self.max_z, other.min_z, other.max_z)
            >= -GEOMETRY_EPSILON_CM
        )

    def overlaps(self, other: AxisAlignedBox) -> bool:
        """Intersección con volumen estrictamente positivo.

        Dos cajas que solo comparten una cara, una arista o un vértice
        NO se superponen (``overlaps`` es ``False`` en ese caso; ver
        ``touches``).
        """
        return (
            _axis_overlap(self.min_x, self.max_x, other.min_x, other.max_x) > GEOMETRY_EPSILON_CM
            and _axis_overlap(self.min_y, self.max_y, other.min_y, other.max_y)
            > GEOMETRY_EPSILON_CM
            and _axis_overlap(self.min_z, self.max_z, other.min_z, other.max_z)
            > GEOMETRY_EPSILON_CM
        )

    def touches(self, other: AxisAlignedBox) -> bool:
        """Contacto (cara, arista o vértice) sin volumen de intersección."""
        return self.intersects(other) and not self.overlaps(other)

    def intersection_volume_cm3(self, other: AxisAlignedBox) -> float:
        overlap_x = max(0.0, _axis_overlap(self.min_x, self.max_x, other.min_x, other.max_x))
        overlap_y = max(0.0, _axis_overlap(self.min_y, self.max_y, other.min_y, other.max_y))
        overlap_z = max(0.0, _axis_overlap(self.min_z, self.max_z, other.min_z, other.max_z))
        return overlap_x * overlap_y * overlap_z


def box_from_placement(placement: Placement) -> AxisAlignedBox:
    """Construye la caja ortoédrica correspondiente a un Placement ya orientado.

    No duplica lógica de dimensiones ni de orientación: reutiliza
    directamente ``placement.position`` y ``placement.orientation.dimensions``.
    """
    return AxisAlignedBox(position=placement.position, dimensions=placement.orientation.dimensions)
