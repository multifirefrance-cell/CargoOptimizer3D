"""Pruebas de expand_load_units."""

from __future__ import annotations

from cargo_optimizer.domain.enums import PackageType
from cargo_optimizer.optimization.expander import expand_load_units
from tests.optimization._helpers import make_load_unit


def test_expands_quantity() -> None:
    unit = make_load_unit(quantity=5)
    instances = expand_load_units((unit,))
    assert len(instances) == 5


def test_instance_numbers_start_at_one() -> None:
    unit = make_load_unit(quantity=3)
    instances = expand_load_units((unit,))
    assert [i.instance_number for i in instances] == [1, 2, 3]


def test_grouped_box_is_not_expanded_by_units_per_package() -> None:
    unit = make_load_unit(package_type=PackageType.GROUPED_BOX, units_per_package=10, quantity=3)
    instances = expand_load_units((unit,))
    assert len(instances) == 3


def test_stable_order_across_multiple_load_units() -> None:
    unit_a = make_load_unit(sku="A", quantity=2)
    unit_b = make_load_unit(sku="B", quantity=2)
    instances = expand_load_units((unit_a, unit_b))
    assert [i.source_order for i in instances] == [0, 1, 2, 3]
    assert [i.load_unit.sku for i in instances] == ["A", "A", "B", "B"]


def test_does_not_modify_load_unit() -> None:
    unit = make_load_unit(quantity=2)
    expand_load_units((unit,))
    assert unit.quantity == 2
