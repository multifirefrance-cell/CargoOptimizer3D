"""Pruebas de `optimization/pattern_packing.py` (fase OPT-17): patrón de filas/capas."""

from __future__ import annotations

from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.optimization.pattern_packing import PatternCursor, generate_grid_positions


def test_first_position_is_the_anchor_itself() -> None:
    anchor = Position3D(0.0, 0.0, 0.0)
    positions = generate_grid_positions(
        anchor,
        x_size_cm=20.0,
        y_size_cm=20.0,
        z_size_cm=20.0,
        length_cm=100.0,
        width_cm=100.0,
        height_cm=100.0,
    )
    assert next(positions) == anchor


def test_fills_a_complete_row_before_the_next_row() -> None:
    anchor = Position3D(0.0, 0.0, 0.0)
    positions = list(
        generate_grid_positions(
            anchor,
            x_size_cm=20.0,
            y_size_cm=20.0,
            z_size_cm=20.0,
            length_cm=50.0,  # caben 2 en X (0, 20); 40+20=60 > 50
            width_cm=100.0,
            height_cm=100.0,
        )
    )
    # Primero toda la fila Y=0 (X=0, X=20), luego la siguiente fila (Y=20).
    assert positions[:2] == [Position3D(0.0, 0.0, 0.0), Position3D(20.0, 0.0, 0.0)]
    assert positions[2] == Position3D(0.0, 20.0, 0.0)


def test_fills_complete_rows_before_the_next_layer() -> None:
    anchor = Position3D(0.0, 0.0, 0.0)
    positions = list(
        generate_grid_positions(
            anchor,
            x_size_cm=50.0,
            y_size_cm=50.0,
            z_size_cm=20.0,
            length_cm=50.0,
            width_cm=100.0,  # caben 2 filas en Y (0, 50)
            height_cm=100.0,
        )
    )
    # Una sola posición por fila (largo=ancho=huella), 2 filas por capa,
    # luego la siguiente capa (Z=20) antes de agotar Z.
    assert positions[:2] == [Position3D(0.0, 0.0, 0.0), Position3D(0.0, 50.0, 0.0)]
    assert positions[2] == Position3D(0.0, 0.0, 20.0)


def test_stops_exactly_at_the_space_boundary() -> None:
    anchor = Position3D(0.0, 0.0, 0.0)
    positions = list(
        generate_grid_positions(
            anchor,
            x_size_cm=30.0,
            y_size_cm=100.0,
            z_size_cm=100.0,
            length_cm=100.0,  # caben exactamente 3 (0, 30, 60); 90+30=120 > 100
            width_cm=100.0,
            height_cm=100.0,
        )
    )
    assert positions == [
        Position3D(0.0, 0.0, 0.0),
        Position3D(30.0, 0.0, 0.0),
        Position3D(60.0, 0.0, 0.0),
    ]


def test_anchor_offset_is_respected_in_every_row_and_layer() -> None:
    """El patrón debe partir siempre del propio `anchor`, no del origen del espacio
    (la primera colocación real puede no estar en (0, 0, 0) si otro SKU ya ocupaba
    esa posición)."""
    anchor = Position3D(10.0, 5.0, 0.0)
    positions = list(
        generate_grid_positions(
            anchor,
            x_size_cm=20.0,
            y_size_cm=20.0,
            z_size_cm=20.0,
            length_cm=55.0,  # 10+20+20=50, +20=70>55: 2 en X
            width_cm=50.0,  # 5+20=25, +20=45<=50: 2 en Y
            height_cm=25.0,  # 1 sola capa
        )
    )
    xs = {p.x_cm for p in positions}
    ys = {p.y_cm for p in positions}
    assert xs == {10.0, 30.0}
    assert ys == {5.0, 25.0}


def test_empty_when_nothing_else_fits() -> None:
    anchor = Position3D(0.0, 0.0, 0.0)
    positions = list(
        generate_grid_positions(
            anchor,
            x_size_cm=200.0,
            y_size_cm=200.0,
            z_size_cm=200.0,
            length_cm=100.0,
            width_cm=100.0,
            height_cm=100.0,
        )
    )
    assert positions == []


def test_pattern_cursor_returns_none_once_exhausted() -> None:
    from cargo_optimizer.domain.dimensions import Dimensions3D
    from cargo_optimizer.domain.enums import OrientationCode
    from cargo_optimizer.domain.orientation import Orientation

    orientation = Orientation.from_base_dimensions(
        Dimensions3D(50.0, 50.0, 50.0), OrientationCode.LWH_XYZ
    )
    positions = generate_grid_positions(
        Position3D(0.0, 0.0, 0.0),
        x_size_cm=50.0,
        y_size_cm=50.0,
        z_size_cm=50.0,
        length_cm=50.0,
        width_cm=50.0,
        height_cm=50.0,
    )
    cursor = PatternCursor(orientation=orientation, orientation_index=0, positions=positions)
    assert cursor.next_position() == Position3D(0.0, 0.0, 0.0)
    assert cursor.next_position() is None  # rejilla agotada (un único hueco)

    cursor.exhausted = True
    fresh_positions = generate_grid_positions(
        Position3D(0.0, 0.0, 0.0), 1.0, 1.0, 1.0, 100.0, 100.0, 100.0
    )
    cursor2 = PatternCursor(orientation=orientation, orientation_index=0, positions=fresh_positions)
    cursor2.exhausted = True
    assert cursor2.next_position() is None
