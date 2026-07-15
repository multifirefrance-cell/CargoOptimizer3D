"""Pruebas de order_instances."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.optimization.expander import expand_load_units
from cargo_optimizer.optimization.ordering import order_instances
from cargo_optimizer.rules.engine import RulesEngine
from tests.optimization._helpers import DEFAULT_SPACE, make_individual_extinguisher, make_load_unit

_ENGINE = RulesEngine()


def test_individual_extinguisher_is_prioritized() -> None:
    normal = make_load_unit(sku="NORMAL", quantity=1)
    extinguisher = make_individual_extinguisher(sku="EXT", nominal_kg=5.0, quantity=1)
    instances = expand_load_units((normal, extinguisher))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "EXT"


def test_single_orientation_is_prioritized_over_multi() -> None:
    single = make_load_unit(
        sku="SINGLE", allowed_orientation_codes=(OrientationCode.LWH_XYZ,), quantity=1
    )
    multi = make_load_unit(sku="MULTI", quantity=1)
    instances = expand_load_units((multi, single))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "SINGLE"


def test_non_stackable_is_prioritized() -> None:
    non_stackable = make_load_unit(sku="NS", max_stack_count=1, quantity=1)
    stackable = make_load_unit(sku="ST", max_stack_count=5, quantity=1)
    instances = expand_load_units((stackable, non_stackable))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "NS"


def test_larger_volume_first() -> None:
    small = make_load_unit(sku="SMALL", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1)
    large = make_load_unit(sku="LARGE", dimensions=Dimensions3D(50.0, 50.0, 50.0), quantity=1)
    instances = expand_load_units((small, large))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "LARGE"


def test_larger_max_dimension_breaks_volume_tie() -> None:
    # Mismo volumen (60*20*20 == 40*30*20 == 24000), distinta dimensión máxima.
    a = make_load_unit(sku="A", dimensions=Dimensions3D(60.0, 20.0, 20.0), quantity=1)
    b = make_load_unit(sku="B", dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=1)
    instances = expand_load_units((b, a))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "A"


def test_heavier_first() -> None:
    light = make_load_unit(sku="LIGHT", weight_kg=5.0, quantity=1)
    heavy = make_load_unit(sku="HEAVY", weight_kg=50.0, quantity=1)
    instances = expand_load_units((light, heavy))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "HEAVY"


def test_sku_breaks_remaining_ties() -> None:
    a = make_load_unit(sku="AAA", quantity=1)
    b = make_load_unit(sku="ZZZ", quantity=1)
    instances = expand_load_units((b, a))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "AAA"


def test_determinism() -> None:
    a = make_load_unit(sku="A", quantity=2)
    b = make_load_unit(sku="B", quantity=2)
    instances = expand_load_units((a, b))
    ordered_1 = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    ordered_2 = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered_1 == ordered_2
