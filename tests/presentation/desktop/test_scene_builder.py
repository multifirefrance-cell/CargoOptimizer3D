"""Pruebas de `SceneBuilder`: sin Qt ni PyVista, función pura sobre datos de dominio."""

from __future__ import annotations

from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.presentation.desktop.viewer.scene_builder import SceneBuilder

_SPACE = LoadingSpace(
    name="Bodega de pruebas",
    category=LoadingSpaceCategory.WAREHOUSE,
    internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
)


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def _placement(unit: LoadUnit, sequence_number: int = 1, instance_number: int = 1) -> Placement:
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.LWH_XYZ)
    return Placement(
        load_unit_id=unit.id,
        instance_number=instance_number,
        position=Position3D(0.0, 0.0, 0.0),
        orientation=orientation,
        sequence_number=sequence_number,
    )


def _result(placements: tuple[Placement, ...]) -> PackingResult:
    return PackingResult(
        loading_space=_SPACE,
        placements=placements,
        unpacked_units=(),
        requested_count=len(placements),
        packed_count=len(placements),
        used_volume_cm3=0.0,
        used_weight_kg=0.0,
        execution_time_seconds=0.01,
        algorithm_name="greedy_extreme_point_v1",
    )


def test_empty_result_produces_empty_scene() -> None:
    scene = SceneBuilder().build(_result(()), {})
    assert scene.loading_space is _SPACE
    assert scene.placement_visuals == ()
    assert scene.color_mapping == {}


def test_known_load_unit_is_translated_faithfully() -> None:
    unit = _unit(sku="BOX-42", name="Caja 42", weight_kg=12.5, color_hex="#123456")
    placement = _placement(unit, sequence_number=3, instance_number=2)
    scene = SceneBuilder().build(_result((placement,)), {unit.id: unit})

    assert len(scene.placement_visuals) == 1
    visual = scene.placement_visuals[0]
    assert visual.sequence_number == 3
    assert visual.instance_number == 2
    assert visual.load_unit_id == unit.id
    assert visual.sku == "BOX-42"
    assert visual.name == "Caja 42"
    assert visual.weight_kg == 12.5
    assert visual.color_hex == "#123456"
    assert visual.package_type == unit.package_type.value
    assert visual.units_per_package == unit.units_per_package
    assert visual.max_stack_count == unit.max_stack_count
    assert visual.is_extinguisher is False
    assert visual.extinguisher_nominal_kg is None
    assert visual.fragile is False
    assert scene.color_mapping["BOX-42"] == "#123456"


def test_position_and_oriented_dimensions_match_placement_properties() -> None:
    unit = _unit()
    orientation = Orientation.from_base_dimensions(unit.dimensions, OrientationCode.WLH_XYZ)
    placement = Placement(
        load_unit_id=unit.id,
        instance_number=1,
        position=Position3D(10.0, 20.0, 30.0),
        orientation=orientation,
        sequence_number=1,
    )
    scene = SceneBuilder().build(_result((placement,)), {unit.id: unit})
    visual = scene.placement_visuals[0]

    assert visual.position == (placement.x_cm, placement.y_cm, placement.z_cm)
    assert visual.oriented_dimensions == (
        placement.length_cm,
        placement.width_cm,
        placement.height_cm,
    )
    assert visual.orientation_code == OrientationCode.WLH_XYZ.value


def test_unknown_load_unit_produces_generic_visual_without_crashing() -> None:
    unknown_unit = _unit()
    placement = _placement(unknown_unit, sequence_number=5)
    # load_units_by_id NO contiene unknown_unit.id: referencia desconocida.
    scene = SceneBuilder().build(_result((placement,)), {})

    assert len(scene.placement_visuals) == 1
    visual = scene.placement_visuals[0]
    assert visual.sequence_number == 5
    assert visual.load_unit_id == unknown_unit.id
    assert visual.sku == "?"
    assert visual.name == "Desconocido"
    assert visual.weight_kg == 0.0
    assert visual.color_hex  # sigue teniendo un color determinista, nunca vacío


def test_unknown_load_unit_gets_deterministic_fallback_color() -> None:
    unit = _unit()
    placement = _placement(unit)
    scene_a = SceneBuilder().build(_result((placement,)), {})
    scene_b = SceneBuilder().build(_result((placement,)), {})
    assert scene_a.placement_visuals[0].color_hex == scene_b.placement_visuals[0].color_hex


def test_extinguisher_fields_are_carried_through() -> None:
    unit = _unit(
        sku="EXT-1",
        dimensions=Dimensions3D(60.0, 20.0, 20.0),
        package_type=PackageType.INDIVIDUAL,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.PQS,
        extinguisher_nominal_kg=5.0,
    )
    placement = _placement(unit)
    scene = SceneBuilder().build(_result((placement,)), {unit.id: unit})
    visual = scene.placement_visuals[0]
    assert visual.is_extinguisher is True
    assert visual.extinguisher_nominal_kg == 5.0


def test_multiple_placements_preserve_sequence_order() -> None:
    unit = _unit()
    placements = tuple(_placement(unit, sequence_number=i, instance_number=i) for i in (1, 2, 3))
    scene = SceneBuilder().build(_result(placements), {unit.id: unit})
    assert [v.sequence_number for v in scene.placement_visuals] == [1, 2, 3]


def test_unrelated_load_unit_ids_do_not_resolve() -> None:
    unit = _unit()
    other_unit = _unit(sku="OTHER")
    placement = _placement(unit)
    scene = SceneBuilder().build(_result((placement,)), {other_unit.id: other_unit})
    visual = scene.placement_visuals[0]
    assert visual.sku == "?"


def test_build_never_raises_for_a_scenario_with_a_dangling_reference() -> None:
    unit = _unit()
    placement = _placement(unit)
    dangling_id = uuid4()
    # load_units_by_id con una clave irrelevante, ninguna coincide con placement.
    scene = SceneBuilder().build(_result((placement,)), {dangling_id: unit})
    assert scene.placement_visuals[0].sku == "?"
