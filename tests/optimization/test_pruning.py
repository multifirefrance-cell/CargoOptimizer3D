"""Pruebas de `optimization.pruning`.

Cubren exactamente los dos criterios de poda documentados: puntos
fuera de límites y puntos estrictamente interiores a una caja
existente. También comprueban que tocar una cara (no colisión) nunca
se poda, y que los códigos de violación garantizados que se devuelven
coinciden con lo que produciría una evaluación completa.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.optimization.pruning import prune_candidate_positions
from cargo_optimizer.rules.codes import COLLISION, OUT_OF_BOUNDS
from tests.optimization._helpers import DEFAULT_SPACE

_EXISTING_BOX = AxisAlignedBox(
    position=Position3D(0.0, 0.0, 0.0), dimensions=Dimensions3D(40.0, 30.0, 20.0)
)


def test_keeps_origin_and_ordinary_points() -> None:
    positions = (Position3D(0.0, 0.0, 0.0), Position3D(40.0, 0.0, 0.0))
    kept, codes = prune_candidate_positions(positions, DEFAULT_SPACE, (_EXISTING_BOX,))
    assert kept == positions
    assert codes == frozenset()


def test_prunes_point_outside_loading_space_bounds() -> None:
    dims = DEFAULT_SPACE.internal_dimensions
    outside = Position3D(dims.length_cm + 10.0, 0.0, 0.0)
    kept, codes = prune_candidate_positions((Position3D(0.0, 0.0, 0.0), outside), DEFAULT_SPACE, ())
    assert outside not in kept
    assert codes == frozenset({OUT_OF_BOUNDS})


def test_does_not_prune_point_exactly_at_the_boundary() -> None:
    dims = DEFAULT_SPACE.internal_dimensions
    at_edge = Position3D(dims.length_cm, 0.0, 0.0)
    kept, codes = prune_candidate_positions((at_edge,), DEFAULT_SPACE, ())
    assert kept == (at_edge,)
    assert codes == frozenset()


def test_prunes_point_strictly_inside_existing_box() -> None:
    inside = Position3D(20.0, 15.0, 10.0)  # centro de _EXISTING_BOX: estrictamente interior
    kept, codes = prune_candidate_positions((inside,), DEFAULT_SPACE, (_EXISTING_BOX,))
    assert kept == ()
    assert codes == frozenset({COLLISION})


def test_does_not_prune_point_touching_existing_box_surface() -> None:
    # Exactamente en la cara superior de _EXISTING_BOX: tocar no es colisión.
    on_surface = Position3D(20.0, 15.0, 20.0)
    kept, codes = prune_candidate_positions((on_surface,), DEFAULT_SPACE, (_EXISTING_BOX,))
    assert kept == (on_surface,)
    assert codes == frozenset()


def test_does_not_prune_point_at_box_corner() -> None:
    corner = Position3D(0.0, 0.0, 0.0)
    kept, codes = prune_candidate_positions((corner,), DEFAULT_SPACE, (_EXISTING_BOX,))
    assert kept == (corner,)
    assert codes == frozenset()


def test_empty_inputs() -> None:
    kept, codes = prune_candidate_positions((), DEFAULT_SPACE, (_EXISTING_BOX,))
    assert kept == ()
    assert codes == frozenset()
