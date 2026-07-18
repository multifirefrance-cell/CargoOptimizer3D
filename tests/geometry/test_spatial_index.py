"""Pruebas de `SpatialIndex`: sin falsos negativos, comportamiento de límites de celda."""

from __future__ import annotations

import itertools
import random

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.collision import boxes_overlap
from cargo_optimizer.geometry.spatial_index import SpatialIndex


def _box(x: float, y: float, z: float, dx: float, dy: float, dz: float) -> AxisAlignedBox:
    return AxisAlignedBox(position=Position3D(x, y, z), dimensions=Dimensions3D(dx, dy, dz))


def test_query_finds_overlapping_box_in_same_cell() -> None:
    index = SpatialIndex(cell_size_cm=50.0)
    box_a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    index.insert(1, box_a)
    query = _box(5.0, 5.0, 5.0, 10.0, 10.0, 10.0)
    assert 1 in index.query_box(query)


def test_query_omits_far_away_box() -> None:
    index = SpatialIndex(cell_size_cm=50.0)
    box_a = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    index.insert(1, box_a)
    query = _box(500.0, 500.0, 500.0, 10.0, 10.0, 10.0)
    assert 1 not in index.query_box(query)


def test_query_at_exact_cell_boundary_still_finds_neighbor() -> None:
    """Dos cajas justo a ambos lados de un límite de celda deben seguir encontrándose."""
    index = SpatialIndex(cell_size_cm=50.0)
    # box_a termina exactamente en x=50 (borde de celda); box_b empieza ahí.
    box_a = _box(40.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    box_b = _box(50.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    index.insert(1, box_a)
    assert 1 in index.query_box(box_b)


def test_empty_index_returns_empty_query() -> None:
    index = SpatialIndex(cell_size_cm=50.0)
    query = _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert index.query_box(query) == frozenset()


def test_no_false_negatives_random_boxes() -> None:
    """Comparación exhaustiva: toda caja que realmente solapa/toca debe aparecer en la consulta.

    No es una prueba de rendimiento: genera cajas aleatorias pequeñas en
    un volumen reducido (para maximizar solapes reales) y verifica, para
    cada caja como "consulta", que el conjunto devuelto por el índice
    incluye TODOS los identificadores cuya caja real solapa o toca la de
    consulta según `boxes_overlap` — la propiedad que hace seguro usar
    el índice como filtro barato antes del narrow-phase real.
    """
    rng = random.Random(20260717)
    boxes: dict[int, AxisAlignedBox] = {}
    index = SpatialIndex(cell_size_cm=15.0)
    for identifier in range(200):
        x, y, z = (rng.uniform(0.0, 100.0) for _ in range(3))
        dx, dy, dz = (rng.uniform(1.0, 30.0) for _ in range(3))
        box = _box(x, y, z, dx, dy, dz)
        boxes[identifier] = box
        index.insert(identifier, box)

    for query_id, query_box in boxes.items():
        found = index.query_box(query_box)
        for other_id, other_box in boxes.items():
            if other_id == query_id:
                continue
            truly_overlaps = boxes_overlap(query_box, other_box) or _touches_or_overlaps(
                query_box, other_box
            )
            if truly_overlaps:
                assert other_id in found, (
                    f"Falso negativo: {other_id} solapa/toca a {query_id} pero no aparece "
                    "en query_box()"
                )


def _touches_or_overlaps(a: AxisAlignedBox, b: AxisAlignedBox) -> bool:
    """True si los intervalos de `a` y `b` se solapan o tocan en los tres ejes."""
    for a_min, a_max, b_min, b_max in (
        (a.min_x, a.max_x, b.min_x, b.max_x),
        (a.min_y, a.max_y, b.min_y, b.max_y),
        (a.min_z, a.max_z, b.min_z, b.max_z),
    ):
        if max(a_min, b_min) > min(a_max, b_max):
            return False
    return True


def test_query_includes_boxes_sharing_only_one_axis_cell_pair() -> None:
    """Cajas alineadas en una rejilla, consulta en la esquina compartida por varias celdas."""
    index = SpatialIndex(cell_size_cm=20.0)
    placed = {}
    for i, (x, y, z) in enumerate(itertools.product((0.0, 20.0, 40.0), repeat=3)):
        box = _box(x, y, z, 5.0, 5.0, 5.0)
        placed[i] = box
        index.insert(i, box)

    query = _box(19.0, 19.0, 19.0, 2.0, 2.0, 2.0)
    found = index.query_box(query)
    # La consulta cruza el límite de celda en los tres ejes: debe encontrar
    # al menos la caja que realmente se solapa/toca (en (20,20,20)).
    overlapping = {i for i, box in placed.items() if _touches_or_overlaps(query, box)}
    assert overlapping.issubset(found)


def test_len_reports_nonzero_cell_count_after_insert() -> None:
    index = SpatialIndex(cell_size_cm=50.0)
    assert len(index) == 0
    index.insert(1, _box(0.0, 0.0, 0.0, 10.0, 10.0, 10.0))
    assert len(index) > 0
