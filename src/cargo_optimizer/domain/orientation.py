"""Orientación ortogonal concreta de un Load Unit dentro de un Loading Space.

No contiene lógica de colisión ni de posicionamiento: solo la
transformación geométrica que decide qué dimensión original de la caja
queda alineada con cada eje (X, Y, Z). La detección de colisiones
pertenece al motor geométrico (fase 2.2 del roadmap, ver
docs/Roadmap.md, no de este modelo de dominio).
"""

from __future__ import annotations

from dataclasses import dataclass

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode

# Para cada código, los índices de (length, width, height) que terminan,
# en ese orden, en (X, Y, Z). Ver el docstring de OrientationCode.
_AXIS_INDICES: dict[OrientationCode, tuple[int, int, int]] = {
    OrientationCode.LWH_XYZ: (0, 1, 2),
    OrientationCode.WLH_XYZ: (1, 0, 2),
    OrientationCode.LHW_XYZ: (0, 2, 1),
    OrientationCode.HWL_XYZ: (2, 1, 0),
    OrientationCode.WHL_XYZ: (1, 2, 0),
    OrientationCode.HLW_XYZ: (2, 0, 1),
}


@dataclass(frozen=True, slots=True)
class Orientation:
    """Una orientación concreta: qué código de rotación y qué extensión resultante por eje.

    ``dimensions`` no son las dimensiones originales de la caja, sino ya
    rotadas: ``dimensions.length_cm`` es la extensión en X,
    ``dimensions.width_cm`` en Y y ``dimensions.height_cm`` en Z. El
    campo ``code`` es lo que permite reconstruir qué dimensión original
    (largo, ancho o alto de la caja) terminó en cada eje.
    """

    code: OrientationCode
    dimensions: Dimensions3D

    @classmethod
    def from_base_dimensions(cls, base: Dimensions3D, code: OrientationCode) -> Orientation:
        indices = _AXIS_INDICES[code]
        values = base.as_tuple()
        rotated = Dimensions3D(values[indices[0]], values[indices[1]], values[indices[2]])
        return cls(code=code, dimensions=rotated)

    @property
    def x_size_cm(self) -> float:
        return self.dimensions.length_cm

    @property
    def y_size_cm(self) -> float:
        return self.dimensions.width_cm

    @property
    def z_size_cm(self) -> float:
        return self.dimensions.height_cm
