"""Integración de la carga por patrón (filas/capas, fase OPT-17) sobre `PackingEngine`.

No prueba `generate_grid_positions`/`PatternCursor` en aislamiento (eso
ya está en `test_pattern_packing.py`): aquí se valida que
`GreedyExtremePointStrategy` los usa correctamente de principio a fin
-- posiciones exactas cuando el patrón se aplica, y una caída
correcta (sin colisiones, sin cajas perdidas ni duplicadas) cuando la
rejilla se agota antes de terminar la cantidad solicitada.
"""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory, OrientationCode
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.geometry.collision import find_overlapping_placements
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from tests.optimization._helpers import make_load_unit

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


def _space(length: float, width: float, height: float) -> LoadingSpace:
    return LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(length, width, height),
    )


def test_large_quantity_is_packed_in_exact_raster_grid_positions() -> None:
    """Cantidad >= el umbral de patrón, espacio con capacidad exacta y sobrada.

    Orientación preferida esperada: `LWH_XYZ` (huella 40x30) porque
    tesela mejor un espacio de 200x100 que `WLH_XYZ` (huella 30x40) --
    floor(200/40)*floor(100/30) = 5*3 = 15, frente a
    floor(200/30)*floor(100/40) = 6*2 = 12. Con capacidad de piso 15 y
    20 unidades solicitadas, se necesita una segunda capa (Z),
    disponible porque height=100 permite floor(100/20)=5 capas.
    """
    space = _space(200.0, 100.0, 100.0)
    quantity = 20
    unit = make_load_unit(dimensions=_DIMS, quantity=quantity)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    assert result.packed_count == quantity
    assert result.unpacked_units == ()
    assert find_overlapping_placements(result.placements) == ()

    positions = sorted(
        (p.position.x_cm, p.position.y_cm, p.position.z_cm) for p in result.placements
    )
    # Rejilla esperada: LWH_XYZ (huella 40x30), 5 columnas en X (0,40,...,160),
    # 3 filas en Y (0,30,60), 15 por capa; las 5 restantes en la capa Z=20.
    expected_first_layer = sorted(
        (x, y, 0.0) for y in (0.0, 30.0, 60.0) for x in (0.0, 40.0, 80.0, 120.0, 160.0)
    )
    expected_second_layer = sorted((x, 0.0, 20.0) for x in (0.0, 40.0, 80.0, 120.0, 160.0))
    assert positions == sorted(expected_first_layer + expected_second_layer)
    assert all(p.orientation.code == OrientationCode.LWH_XYZ for p in result.placements)


def test_pattern_falls_back_gracefully_when_grid_is_exhausted() -> None:
    """La rejilla solo tiene capacidad exacta para 3; se piden 6.

    Espacio 100x50x20 (una sola capa en Z: height==box height).
    `WLH_XYZ` (huella 30x40) tesela mejor: floor(100/30)*floor(50/40) =
    3*1 = 3, frente a `LWH_XYZ` floor(100/40)*floor(50/30) = 2*1 = 2 --
    orientación preferida real: `WLH_XYZ`. Tras colocar las 3 que caben
    por patrón, la rejilla se agota (`PatternCursor.next_position() is
    None`) y cae a la búsqueda general (ronda 1, misma orientación) y
    luego a la ronda 2 (todas las orientaciones) para las 3 restantes
    -- ninguna cabe geométricamente (no queda hueco real, ver
    docstring del test), así que deben quedar como `UnpackedUnit`, sin
    colisión ni pérdida/duplicado de cajas.
    """
    space = _space(100.0, 50.0, 20.0)
    quantity = 6
    unit = make_load_unit(dimensions=_DIMS, quantity=quantity)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    result = PackingEngine().optimize(request)

    assert result.packed_count == 3
    assert len(result.unpacked_units) == 3
    assert find_overlapping_placements(result.placements) == ()

    positions = sorted(
        (p.position.x_cm, p.position.y_cm, p.position.z_cm) for p in result.placements
    )
    assert positions == [(0.0, 0.0, 0.0), (30.0, 0.0, 0.0), (60.0, 0.0, 0.0)]
    assert all(p.orientation.code == OrientationCode.WLH_XYZ for p in result.placements)
