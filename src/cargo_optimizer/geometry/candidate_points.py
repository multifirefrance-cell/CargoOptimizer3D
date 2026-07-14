"""Generación de puntos candidatos de colocación.

Esta fase no implementa optimización ni heurísticas de selección:
solo la generación geométrica básica de los puntos "esquina" obvios que
un motor de optimización futuro (fase 4) podrá usar como punto de
partida.
"""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM


def _is_close(a: float, b: float) -> bool:
    return abs(a - b) <= GEOMETRY_EPSILON_CM


def _same_position(a: Position3D, b: Position3D) -> bool:
    return _is_close(a.x_cm, b.x_cm) and _is_close(a.y_cm, b.y_cm) and _is_close(a.z_cm, b.z_cm)


def _dedupe_positions(positions: list[Position3D]) -> list[Position3D]:
    unique: list[Position3D] = []
    for candidate in positions:
        if not any(_same_position(candidate, kept) for kept in unique):
            unique.append(candidate)
    return unique


def generate_candidate_positions(placements: Sequence[Placement]) -> tuple[Position3D, ...]:
    """Puntos candidatos derivados geométricamente de los Placements existentes.

    Incluye el origen `(0, 0, 0)` y, por cada Placement, el punto al
    final de su extensión en X, el punto al final de su extensión en Y
    y el punto en su cara superior en Z (cada uno manteniendo las otras
    dos coordenadas en la esquina de origen de esa caja). No filtra
    todavía por límites del Loading Space ni por colisiones, y no
    aplica ninguna heurística de optimización.
    """
    positions: list[Position3D] = [Position3D(0.0, 0.0, 0.0)]
    for placement in placements:
        box = box_from_placement(placement)
        positions.append(Position3D(box.max_x, box.min_y, box.min_z))
        positions.append(Position3D(box.min_x, box.max_y, box.min_z))
        positions.append(Position3D(box.min_x, box.min_y, box.max_z))

    unique = _dedupe_positions(positions)
    unique.sort(key=lambda p: (p.z_cm, p.x_cm, p.y_cm))
    return tuple(unique)
