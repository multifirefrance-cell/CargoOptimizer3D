"""Escenarios realistas de extintores sobre PackingEngine (sección 24 del encargo)."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    ExtinguisherAgent,
    LoadingSpaceCategory,
    OrientationCode,
    PackageType,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from cargo_optimizer.rules.extinguisher_rules import (
    is_grouped_small_extinguisher,
    is_individual_large_extinguisher,
)
from tests.optimization._helpers import DEFAULT_SPACE


def _individual_extinguisher(
    sku: str,
    gross_weight_kg: float,
    nominal_kg: float,
    agent: ExtinguisherAgent,
    **overrides: object,
) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": sku,
        "name": f"Extintor {agent.value} {nominal_kg:g}kg",
        "dimensions": Dimensions3D(60.0, 20.0, 20.0),
        "weight_kg": gross_weight_kg,
        "package_type": PackageType.INDIVIDUAL,
        "is_extinguisher": True,
        "extinguisher_agent": agent,
        "extinguisher_nominal_kg": nominal_kg,
        "quantity": 1,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def _grouped_extinguisher(
    sku: str, nominal_kg: float, units_per_package: int, **overrides: object
) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": sku,
        "name": f"Caja grupal {nominal_kg:g}kg",
        "dimensions": Dimensions3D(50.0, 40.0, 30.0),
        "weight_kg": 12.0,
        "package_type": PackageType.GROUPED_BOX,
        "units_per_package": units_per_package,
        "is_extinguisher": True,
        "extinguisher_agent": ExtinguisherAgent.PQS,
        "extinguisher_nominal_kg": nominal_kg,
        "quantity": 3,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


# A. Extintor PQS 10 kg individual ---------------------------------------------------


def test_pqs_10kg_individual_stays_horizontal_axis_x_level_1() -> None:
    unit = _individual_extinguisher(
        "PQS-10", gross_weight_kg=13.5, nominal_kg=10.0, agent=ExtinguisherAgent.PQS
    )
    assert unit.weight_kg != unit.extinguisher_nominal_kg
    assert is_individual_large_extinguisher(unit)

    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 1
    placement = result.placements[0]
    assert placement.orientation.code in (OrientationCode.LWH_XYZ, OrientationCode.LHW_XYZ)
    assert placement.z_cm == 0.0


# B. CO2 5 kg individual --------------------------------------------------------------


def test_co2_5kg_individual_has_same_restriction() -> None:
    unit = _individual_extinguisher(
        "CO2-5", gross_weight_kg=8.0, nominal_kg=5.0, agent=ExtinguisherAgent.CO2
    )
    assert is_individual_large_extinguisher(unit)

    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 1
    placement = result.placements[0]
    assert placement.orientation.code in (OrientationCode.LWH_XYZ, OrientationCode.LHW_XYZ)


# B.1 Un extintor individual >= 3 kg apila hasta su propio max_stack_count -----------
# (ya no existe ninguna excepción automática que lo fuerce a 1 — ver
# docs/OptimizerPerformance.md, "Fase OPT-15").


def test_individual_large_extinguisher_stacks_up_to_its_own_configured_limit() -> None:
    unit = _individual_extinguisher(
        "PQS-STACK",
        gross_weight_kg=13.5,
        nominal_kg=10.0,
        agent=ExtinguisherAgent.PQS,
        max_stack_count=3,
        quantity=3,
    )
    # Espacio con un único hueco de piso (60x20 cm): solo apilando se
    # colocan las 3 unidades, nunca esparciéndolas en el suelo.
    single_footprint_space = LoadingSpace(
        name="Hueco único de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(60.0, 20.0, 100.0),
    )
    request = PackingRequest(loading_space=single_footprint_space, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 3
    assert result.unpacked_units == ()
    z_levels = sorted({p.position.z_cm for p in result.placements})
    assert z_levels == [0.0, 20.0, 40.0]


def test_individual_large_extinguisher_with_limit_one_does_not_stack() -> None:
    unit = _individual_extinguisher(
        "PQS-NOSTACK",
        gross_weight_kg=13.5,
        nominal_kg=10.0,
        agent=ExtinguisherAgent.PQS,
        max_stack_count=1,
        quantity=3,
    )
    single_footprint_space = LoadingSpace(
        name="Hueco único de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(60.0, 20.0, 100.0),
    )
    request = PackingRequest(loading_space=single_footprint_space, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 1
    assert len(result.unpacked_units) == 2


# C/D/E. Cajas grupales 1/2/3 kg --------------------------------------------------------


def test_pqs_1kg_grouped_box_units_per_package_10() -> None:
    unit = _grouped_extinguisher("PQS-GRP-1", nominal_kg=1.0, units_per_package=10)
    assert is_grouped_small_extinguisher(unit)
    assert not is_individual_large_extinguisher(unit)

    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 3
    assert result.requested_count == 3  # cajas, no extintores internos (30)


def test_pqs_2kg_grouped_box_units_per_package_8() -> None:
    unit = _grouped_extinguisher("PQS-GRP-2", nominal_kg=2.0, units_per_package=8)
    assert is_grouped_small_extinguisher(unit)

    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 3


def test_pqs_3kg_grouped_box_units_per_package_6_not_large_individual() -> None:
    unit = _grouped_extinguisher("PQS-GRP-3", nominal_kg=3.0, units_per_package=6)
    assert is_grouped_small_extinguisher(unit)
    assert not is_individual_large_extinguisher(unit)

    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 3


# F. Capacidad grupal personalizada: warning, no rechazo -------------------------------


def test_custom_grouped_capacity_generates_warning_but_still_packs() -> None:
    unit = _grouped_extinguisher("PQS-CUSTOM", nominal_kg=1.0, units_per_package=15, quantity=1)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    result = PackingEngine().optimize(request)

    assert result.packed_count == 1
    assert result.unpacked_units == ()
    assert any("recomiendan" in warning for warning in result.warnings)
