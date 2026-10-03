"""Generación de posiciones en patrón regular (filas, luego capas) — fase OPT-17.

Motivación (ver `docs/OptimizerPerformance.md`, "Fase OPT-17"): cuando
un mismo `LoadUnit` tiene una cantidad grande de instancias idénticas,
`GreedyExtremePointStrategy` seguía resolviendo cada instancia — tras
la primera — con una búsqueda completa entre todos los puntos
candidatos disponibles (aunque acotada por el corte temprano exacto de
la fase OPT-16), pese a que, en el caso típico de una zona vacía y una
única orientación fija por ronda, la siguiente posición válida es
**geométricamente predecible** a partir de la anterior: la misma fila
(avanzando en X), la siguiente fila (avanzando en Y, misma capa), o la
siguiente capa (avanzando en Z).

`generate_grid_positions` no sustituye ninguna regla de negocio ni de
geometría: solo produce candidatos *plausibles* (dentro de los límites
del Loading Space), en el mismo orden de preferencia que ya usa el
resto del motor (`z` creciente, luego `x`, luego `y` — igual que
`geometry.candidate_points.generate_candidate_positions` y
`optimization.scoring.score_candidate`). Cada posición generada sigue
pasando por `RulesEngine.evaluate_placement` completo (colisión,
soporte, apilamiento, peso, fragilidad, orientación, extintor) antes de
aceptarse — nunca se salta ninguna regla. En cuanto una posición
generada resulta inválida (colisión con otro SKU ya colocado, límite
de apilamiento alcanzado, fuera de los límites reales, etc.), quien
consume el generador debe dejar de usarlo y volver a la búsqueda
general (`GreedyExtremePointStrategy._try_place_instance`) — ver
`PatternCursor.exhausted`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM


def generate_grid_positions(
    anchor: Position3D,
    x_size_cm: float,
    y_size_cm: float,
    z_size_cm: float,
    length_cm: float,
    width_cm: float,
    height_cm: float,
    max_start_z: float | None = None,
) -> Iterator[Position3D]:
    """Rejilla regular a partir de `anchor`, avanzando primero en X (fila), luego en
    Y (siguiente fila, misma capa), luego en Z (siguiente capa) — "filas completas,
    después capas completas", tal cual pide el encargo. El primer valor producido es
    el propio `anchor`; quien lo consuma para reutilizar una posición ya colocada
    debe descartar ese primer valor.

    `max_start_z`: si se especifica, el generador se detiene antes de producir
    cualquier posición cuyo z_cm sea >= max_start_z. Se usa cuando el cursor ancla
    en la zona y_gap (z < min_z del bloque anterior) para evitar que escale
    verticalmente por encima del techo del SKU anterior formando un "muro".

    No verifica colisiones, soporte, apilamiento ni ninguna otra regla: eso es
    responsabilidad de `RulesEngine.evaluate_placement` sobre cada posición
    producida. Esta función es pura geometría de rejilla, siempre determinista.
    """
    z = anchor.z_cm
    while z + z_size_cm <= height_cm + GEOMETRY_EPSILON_CM:
        if max_start_z is not None and z >= max_start_z - GEOMETRY_EPSILON_CM:
            return
        y = anchor.y_cm
        while y + y_size_cm <= width_cm + GEOMETRY_EPSILON_CM:
            x = anchor.x_cm
            while x + x_size_cm <= length_cm + GEOMETRY_EPSILON_CM:
                yield Position3D(x, y, z)
                x += x_size_cm
            y += y_size_cm
        z += z_size_cm


@dataclass(slots=True)
class PatternCursor:
    """Estado de un patrón de filas/capas en curso para un `LoadUnit` concreto.

    `exhausted=True` significa "el patrón ya falló una vez (posición
    fuera de límites, colisión con otro SKU, límite de apilamiento
    alcanzado, etc.) o se agotó la rejilla": a partir de ahí,
    `GreedyExtremePointStrategy` deja de intentarlo para el resto de
    instancias de este `LoadUnit` en esta ronda y vuelve, de forma
    permanente y sin ambigüedad, a la búsqueda general — el mismo
    comportamiento, resultado y garantías que sin esta optimización.
    """

    orientation: Orientation
    orientation_index: int
    positions: Iterator[Position3D]
    exhausted: bool = False
    max_start_z: float | None = None

    def next_position(self) -> Position3D | None:
        """Siguiente posición de la rejilla, o `None` si ya no quedan dentro de límites."""
        if self.exhausted:
            return None
        return next(self.positions, None)
