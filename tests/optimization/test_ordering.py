"""Pruebas de order_instances."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.optimization.expander import expand_load_units
from cargo_optimizer.optimization.ordering import order_instances
from cargo_optimizer.rules.engine import RulesEngine
from tests.optimization._helpers import DEFAULT_SPACE, make_individual_extinguisher, make_load_unit

_ENGINE = RulesEngine()


def test_individual_extinguisher_with_larger_max_dim_goes_first() -> None:
    # Regla nueva: ordenamiento por volumen total. Si volumen es igual, desempata
    # la dimensión máxima. El extintor (max=60) supera a la caja normal (max=40).
    normal = make_load_unit(sku="NORMAL", quantity=1)      # 40×30×20 = 24 000 cm³
    extinguisher = make_individual_extinguisher(sku="EXT", nominal_kg=5.0, quantity=1)  # 60×20×20 = 24 000 cm³
    instances = expand_load_units((normal, extinguisher))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "EXT"


def test_orientation_count_no_longer_affects_order() -> None:
    # Las restricciones de orientación ya NO alteran la prioridad de carga.
    # Con igual volumen y dimensiones, el desempate es alfabético (SKU).
    single = make_load_unit(
        sku="SINGLE", allowed_orientation_codes=(OrientationCode.LWH_XYZ,), quantity=1
    )
    multi = make_load_unit(sku="MULTI", quantity=1)
    instances = expand_load_units((multi, single))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    # "MULTI" < "SINGLE" alfabéticamente → MULTI primero (volumen y dims iguales)
    assert ordered[0].load_unit.sku == "MULTI"


def test_non_stackable_not_prioritized_by_stack_count() -> None:
    # max_stack_count ya NO altera la prioridad de carga.
    # Con igual volumen y dims, el desempate es alfabético (SKU).
    non_stackable = make_load_unit(sku="NS", max_stack_count=1, quantity=1)
    stackable = make_load_unit(sku="ST", max_stack_count=5, quantity=1)
    instances = expand_load_units((stackable, non_stackable))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    # "NS" < "ST" alfabéticamente → NS primero (coincide con el resultado anterior
    # pero ahora por razón diferente: SKU, no restricción de apilamiento)
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


# ── loading_priority ────────────────────────────────────────────────────────

def test_loading_priority_1_goes_before_auto() -> None:
    # SKU con prio=1 (fondo explícito) debe ir ANTES que SKU automático,
    # incluso si el automático tiene mucho más volumen total.
    big_auto = make_load_unit(
        sku="BIG", dimensions=Dimensions3D(50.0, 50.0, 50.0), quantity=10
    )  # volumen total = 1 250 000 cm³
    small_prio1 = make_load_unit(
        sku="SMALL", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=1
    )  # volumen total = 1 000 cm³
    instances = expand_load_units((big_auto, small_prio1))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "SMALL"


def test_loading_priority_99_goes_after_auto() -> None:
    # SKU con prio=99 (techo explícito) debe ir DESPUÉS que SKU automático,
    # incluso si el automático tiene mucho menos volumen total.
    small_auto = make_load_unit(
        sku="SMALL", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1
    )
    big_prio99 = make_load_unit(
        sku="BIG", dimensions=Dimensions3D(50.0, 50.0, 50.0), quantity=10, loading_priority=99
    )
    instances = expand_load_units((big_prio99, small_auto))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "SMALL"
    assert ordered[-1].load_unit.sku == "BIG"


def test_loading_priority_bottom_tier_sorted_by_priority_asc() -> None:
    # Entre SKUs del fondo explícito (prio 1-49), prio menor = antes.
    prio5 = make_load_unit(sku="P5", quantity=1, loading_priority=5)
    prio2 = make_load_unit(sku="P2", quantity=1, loading_priority=2)
    prio10 = make_load_unit(sku="P10", quantity=1, loading_priority=10)
    instances = expand_load_units((prio10, prio5, prio2))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    skus = [inst.load_unit.sku for inst in ordered]
    assert skus == ["P2", "P5", "P10"]


def test_loading_priority_top_tier_sorted_by_priority_asc() -> None:
    # Entre SKUs del techo explícito (prio 50-99), prio menor = antes.
    prio60 = make_load_unit(sku="P60", quantity=1, loading_priority=60)
    prio50 = make_load_unit(sku="P50", quantity=1, loading_priority=50)
    prio99 = make_load_unit(sku="P99", quantity=1, loading_priority=99)
    instances = expand_load_units((prio60, prio99, prio50))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    skus = [inst.load_unit.sku for inst in ordered]
    assert skus == ["P50", "P60", "P99"]


def test_loading_priority_zero_behaves_as_auto_volume_order() -> None:
    # loading_priority=0 no altera el orden por volumen (comportamiento anterior).
    small = make_load_unit(sku="SMALL", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=0)
    large = make_load_unit(sku="LARGE", dimensions=Dimensions3D(50.0, 50.0, 50.0), quantity=1, loading_priority=0)
    instances = expand_load_units((small, large))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    assert ordered[0].load_unit.sku == "LARGE"


def test_loading_priority_full_spectrum() -> None:
    # Orden correcto: prio-fondo (1,10) → auto (por volumen) → prio-techo (50,99).
    bottom1 = make_load_unit(sku="BOT1", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=1)
    bottom10 = make_load_unit(sku="BOT10", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=10)
    auto_big = make_load_unit(sku="AUTO_BIG", dimensions=Dimensions3D(50.0, 50.0, 50.0), quantity=1)
    auto_small = make_load_unit(sku="AUTO_SMALL", dimensions=Dimensions3D(20.0, 20.0, 20.0), quantity=1)
    top50 = make_load_unit(sku="TOP50", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=50)
    top99 = make_load_unit(sku="TOP99", dimensions=Dimensions3D(10.0, 10.0, 10.0), quantity=1, loading_priority=99)
    instances = expand_load_units((top99, auto_small, bottom10, auto_big, top50, bottom1))
    ordered = order_instances(instances, DEFAULT_SPACE, _ENGINE)
    skus = [inst.load_unit.sku for inst in ordered]
    assert skus[0] == "BOT1"
    assert skus[1] == "BOT10"
    assert skus[2] == "AUTO_BIG"    # mayor volumen entre los automáticos
    assert skus[3] == "AUTO_SMALL"
    assert skus[4] == "TOP50"
    assert skus[5] == "TOP99"
