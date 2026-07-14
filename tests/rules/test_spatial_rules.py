"""Pruebas de evaluate_bounds, evaluate_collision y evaluate_support."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.rules.codes import COLLISION, OUT_OF_BOUNDS, UNSUPPORTED
from cargo_optimizer.rules.spatial_rules import (
    evaluate_bounds,
    evaluate_collision,
    evaluate_support,
)
from tests.rules._helpers import make_context, make_load_unit, make_placement

_DIMS = Dimensions3D(40.0, 30.0, 20.0)


# --- Espacio -----------------------------------------------------------------------


def test_within_bounds() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(10.0, 10.0, 0.0))
    assert evaluate_bounds(context).is_allowed


def test_out_of_bounds_x() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(990.0, 0.0, 0.0))
    result = evaluate_bounds(context)
    assert not result.is_allowed
    assert result.violations[0].code == OUT_OF_BOUNDS


def test_out_of_bounds_y() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 190.0, 0.0))
    assert not evaluate_bounds(context).is_allowed


def test_out_of_bounds_z() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 190.0))
    assert not evaluate_bounds(context).is_allowed


def test_contact_with_wall_is_allowed() -> None:
    # El espacio de prueba mide 1000x200x200; una caja de 40x30x20 en (960,170,180)
    # toca exactamente el límite (max_x=1000, max_y=200, max_z=200).
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(960.0, 170.0, 180.0))
    assert evaluate_bounds(context).is_allowed


# --- Colisiones ----------------------------------------------------------------


def test_no_collision() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    existing_unit = make_load_unit(sku="OTHER", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(500.0, 0.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 0.0),
        existing_placements=(existing,),
        load_units_by_id={unit.id: unit, existing_unit.id: existing_unit},
    )
    assert evaluate_collision(context).is_allowed


def test_overlap_is_collision() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    existing_unit = make_load_unit(sku="OTHER", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(5.0, 5.0, 5.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 0.0),
        existing_placements=(existing,),
        load_units_by_id={unit.id: unit, existing_unit.id: existing_unit},
    )
    result = evaluate_collision(context)
    assert not result.is_allowed
    assert result.violations[0].code == COLLISION


def test_face_contact_is_allowed() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    existing_unit = make_load_unit(sku="OTHER", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(40.0, 0.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 0.0),
        existing_placements=(existing,),
        load_units_by_id={unit.id: unit, existing_unit.id: existing_unit},
    )
    assert evaluate_collision(context).is_allowed


def test_edge_contact_is_allowed() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    existing_unit = make_load_unit(sku="OTHER", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(40.0, 30.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 0.0),
        existing_placements=(existing,),
        load_units_by_id={unit.id: unit, existing_unit.id: existing_unit},
    )
    assert evaluate_collision(context).is_allowed


def test_vertex_contact_is_allowed() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    existing_unit = make_load_unit(sku="OTHER", dimensions=_DIMS)
    existing = make_placement(existing_unit, Position3D(40.0, 30.0, 20.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 0.0),
        existing_placements=(existing,),
        load_units_by_id={unit.id: unit, existing_unit.id: existing_unit},
    )
    assert evaluate_collision(context).is_allowed


# --- Soporte -----------------------------------------------------------------------


def test_ground_is_supported() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 0.0))
    assert evaluate_support(context).is_allowed


def test_full_support() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    lower_unit = make_load_unit(sku="LOWER", dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={unit.id: unit, lower_unit.id: lower_unit},
    )
    assert evaluate_support(context).is_allowed


def test_partial_support_rejected_by_default() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    lower_unit = make_load_unit(sku="LOWER", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={unit.id: unit, lower_unit.id: lower_unit},
    )
    result = evaluate_support(context)
    assert not result.is_allowed
    assert result.violations[0].code == UNSUPPORTED


def test_partial_support_allowed_with_lower_ratio() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    lower_unit = make_load_unit(sku="LOWER", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower,),
        load_units_by_id={unit.id: unit, lower_unit.id: lower_unit},
    )
    assert evaluate_support(context, minimum_support_ratio=0.4).is_allowed


def test_no_support_is_rejected() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    context = make_context(unit, position=Position3D(0.0, 0.0, 50.0))
    assert not evaluate_support(context).is_allowed


def test_supported_by_two_boxes() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    left_unit = make_load_unit(sku="LEFT", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    right_unit = make_load_unit(sku="RIGHT", dimensions=Dimensions3D(20.0, 30.0, 20.0))
    left = make_placement(left_unit, Position3D(0.0, 0.0, 0.0))
    right = make_placement(right_unit, Position3D(20.0, 0.0, 0.0), sequence_number=2)
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(left, right),
        load_units_by_id={unit.id: unit, left_unit.id: left_unit, right_unit.id: right_unit},
    )
    assert evaluate_support(context).is_allowed


def test_overlapping_support_areas_are_not_double_counted() -> None:
    unit = make_load_unit(dimensions=_DIMS)
    lower_unit = make_load_unit(sku="LOWER", dimensions=_DIMS)
    duplicate_unit = make_load_unit(sku="DUP", dimensions=_DIMS)
    lower = make_placement(lower_unit, Position3D(0.0, 0.0, 0.0))
    duplicate = make_placement(duplicate_unit, Position3D(0.0, 0.0, 0.0), sequence_number=2)
    context = make_context(
        unit,
        position=Position3D(0.0, 0.0, 20.0),
        existing_placements=(lower, duplicate),
        load_units_by_id={
            unit.id: unit,
            lower_unit.id: lower_unit,
            duplicate_unit.id: duplicate_unit,
        },
    )
    assert evaluate_support(context).is_allowed
