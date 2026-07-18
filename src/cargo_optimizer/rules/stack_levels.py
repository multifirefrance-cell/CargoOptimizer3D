"""Cálculo no recursivo del nivel de apilamiento de un `Placement`.

Extraído como módulo propio (fase OPT-13) porque tanto
`rules.context.PlacementRuleContext` (para su propiedad
`stack_level_by_sequence_number`) como `rules.stacking_rules` (para
`evaluate_stack_count`) necesitan estas funciones, y `stacking_rules`
ya importa `context` — este módulo no importa ninguno de los dos, para
no introducir un ciclo.

Ninguna función de aquí es recursiva: `compute_stack_levels` procesa
los placements ordenados por altura ascendente en una única pasada
lineal, de modo que el nivel de cualquier soporte directo real ya está
calculado cuando se necesita (ver docstring de esa función).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.geometry.spatial_index import SpatialIndex
from cargo_optimizer.geometry.support import horizontal_overlap_area_cm2

__all__ = [
    "compute_stack_levels",
    "find_direct_supporting_placements",
    "stack_level_of",
]


def _box_of(
    placement: Placement, box_by_sequence_number: Mapping[int, AxisAlignedBox] | None
) -> AxisAlignedBox:
    """Caja de `placement`: O(1) con mapa precalculado, si no recalcula igual que antes."""
    if box_by_sequence_number is not None:
        return box_by_sequence_number[placement.sequence_number]
    return box_from_placement(placement)


def _nearby_placements(
    candidate_box: AxisAlignedBox,
    existing_placements: Sequence[Placement],
    spatial_index: SpatialIndex | None,
) -> Sequence[Placement]:
    """`existing_placements`, filtrados vía índice espacial cuando está disponible.

    Sin índice (`None`), devuelve `existing_placements` completo —
    idéntico al comportamiento anterior a la fase OPT-11.
    """
    if spatial_index is None:
        return existing_placements
    nearby = spatial_index.query_box(candidate_box)
    return [p for p in existing_placements if p.sequence_number in nearby]


def find_direct_supporting_placements(
    candidate_box: AxisAlignedBox,
    existing_placements: Sequence[Placement],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
    spatial_index: SpatialIndex | None = None,
) -> tuple[Placement, ...]:
    """Placements cuya cara superior toca la base de `candidate_box` con solape positivo."""
    result: list[Placement] = []
    for placement in _nearby_placements(candidate_box, existing_placements, spatial_index):
        box = _box_of(placement, box_by_sequence_number)
        if abs(box.max_z - candidate_box.min_z) > GEOMETRY_EPSILON_CM:
            continue
        if horizontal_overlap_area_cm2(candidate_box, box) <= GEOMETRY_EPSILON_CM:
            continue
        result.append(placement)
    return tuple(result)


def stack_level_of(
    candidate_box: AxisAlignedBox,
    direct_supporters: Sequence[Placement],
    level_by_sequence_number: Mapping[int, int],
) -> int:
    """Nivel de apilamiento de `candidate_box` a partir de sus soportes **directos**.

    No recursivo: asume que `level_by_sequence_number` ya contiene el
    nivel de cada soporte directo. Convención: una caja en el suelo
    está en nivel 1; una caja apoyada en una o más cajas está en
    `1 + max(nivel de cada soporte directo)` (la convención más
    restrictiva cuando el soporte proviene de niveles distintos).
    """
    if candidate_box.min_z <= GEOMETRY_EPSILON_CM:
        return 1
    if not direct_supporters:
        return 1
    return 1 + max(level_by_sequence_number[s.sequence_number] for s in direct_supporters)


def compute_stack_levels(
    existing_placements: Sequence[Placement],
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
    spatial_index: SpatialIndex | None = None,
) -> dict[int, int]:
    """Nivel de apilamiento de cada `Placement` en `existing_placements`, en una única pasada.

    Procesa los placements ordenados por altura (`min_z`) ascendente:
    al llegar a cada uno, cualquier soporte directo real ya tiene menor
    `min_z` y por tanto ya fue procesado, así que su nivel se calcula
    en una pasada lineal, nunca recorriendo la cadena de soporte hacia
    arriba de forma recursiva.
    """
    levels: dict[int, int] = {}
    ordered = sorted(existing_placements, key=lambda p: _box_of(p, box_by_sequence_number).min_z)
    for placement in ordered:
        box = _box_of(placement, box_by_sequence_number)
        supporters = find_direct_supporting_placements(
            box, existing_placements, box_by_sequence_number, spatial_index
        )
        levels[placement.sequence_number] = stack_level_of(box, supporters, levels)
    return levels
