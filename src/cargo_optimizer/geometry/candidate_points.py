"""Generación de puntos candidatos de colocación.

Esta fase no implementa optimización ni heurísticas de selección:
solo la generación geométrica básica de los puntos "esquina" obvios que
un motor de optimización futuro (fase 4) podrá usar como punto de
partida.

`_dedupe_positions` (fase OPT-12, optimización de rendimiento pura —
ver `docs/OptimizerPerformance.md`) usaba originalmente un recorrido
`any(...)` de cada candidato contra todos los puntos ya conservados:
O(m²) sobre los ~3n+1 puntos generados por instancia, uno de los
cuellos de botella cúbicos identificados junto a
`optimization/pruning.py`. La versión actual bucketiza los puntos en
una rejilla de celda `_DEDUPE_CELL_SIZE_CM` (mucho mayor que
`GEOMETRY_EPSILON_CM`, mucho menor que cualquier distancia real entre
puntos candidatos distintos) y solo compara cada candidato contra los
puntos ya vistos en su celda y en las 26 celdas vecinas — mismo
razonamiento de relleno de frontera ya validado en
`geometry/spatial_index.py`. La igualdad final entre dos puntos sigue
decidiéndose siempre con `_same_position` (epsilon exacto): la rejilla
solo acota cuántas comparaciones hacen falta, nunca decide por sí
misma. Mismo resultado que el `any()` original en todos los casos,
nunca una aproximación.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM

_DEDUPE_CELL_SIZE_CM = 1e-6
"""Tamaño de celda para bucketizar puntos candidatos en `_dedupe_positions`.

1000x mayor que `GEOMETRY_EPSILON_CM` (1e-9 cm): dos puntos a menos de
`GEOMETRY_EPSILON_CM` de distancia caen siempre en la misma celda o en
una celda directamente adyacente, nunca más lejos — por eso basta con
revisar las 26 celdas vecinas (más la propia) para no omitir ningún
duplicado real.
"""

_Cell = tuple[int, int, int]


def _is_close(a: float, b: float) -> bool:
    return abs(a - b) <= GEOMETRY_EPSILON_CM


def _same_position(a: Position3D, b: Position3D) -> bool:
    return _is_close(a.x_cm, b.x_cm) and _is_close(a.y_cm, b.y_cm) and _is_close(a.z_cm, b.z_cm)


def _cell_of(position: Position3D) -> _Cell:
    return (
        int(position.x_cm // _DEDUPE_CELL_SIZE_CM),
        int(position.y_cm // _DEDUPE_CELL_SIZE_CM),
        int(position.z_cm // _DEDUPE_CELL_SIZE_CM),
    )


def _dedupe_positions(positions: list[Position3D]) -> list[Position3D]:
    unique: list[Position3D] = []
    buckets: dict[_Cell, list[int]] = defaultdict(list)
    for candidate in positions:
        cx, cy, cz = _cell_of(candidate)
        is_duplicate = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for kept_index in buckets.get((cx + dx, cy + dy, cz + dz), ()):
                        if _same_position(candidate, unique[kept_index]):
                            is_duplicate = True
                            break
                if is_duplicate:
                    break
            if is_duplicate:
                break
        if not is_duplicate:
            buckets[(cx, cy, cz)].append(len(unique))
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
