"""Detección de colisiones entre Placements.

Implementación O(n²), deliberadamente simple para esta fase: cada
Placement se compara con todos los demás. Es correcta y suficiente para
los volúmenes de datos actuales. Si una fase futura (optimización a
gran escala) lo requiere, esta implementación podrá sustituirse por una
estructura espacial (p. ej. un R-tree o una rejilla) sin cambiar la
firma pública de estas funciones.
"""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement


def boxes_overlap(box_a: AxisAlignedBox, box_b: AxisAlignedBox) -> bool:
    """Colisión = intersección con volumen positivo. Tocarse no cuenta como colisión."""
    return box_a.overlaps(box_b)


def placement_overlaps_any(candidate: Placement, existing: Sequence[Placement]) -> bool:
    candidate_box = box_from_placement(candidate)
    return any(boxes_overlap(candidate_box, box_from_placement(other)) for other in existing)


def find_overlapping_placements(
    placements: Sequence[Placement],
) -> tuple[tuple[Placement, Placement], ...]:
    """Todos los pares de Placements que colisionan entre sí.

    Determinista: recorre `placements` en su orden de entrada y solo
    compara cada par (i, j) con i < j, por lo que no hay pares
    duplicados ni comparaciones de un Placement consigo mismo.
    """
    boxes = [box_from_placement(p) for p in placements]
    pairs: list[tuple[Placement, Placement]] = []
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            if boxes_overlap(boxes[i], boxes[j]):
                pairs.append((placements[i], placements[j]))
    return tuple(pairs)
