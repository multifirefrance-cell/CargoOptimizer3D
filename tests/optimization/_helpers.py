"""Fábricas compartidas para los tests de `cargo_optimizer.optimization`."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, LoadingSpaceCategory, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace

DEFAULT_SPACE = LoadingSpace(
    name="Camión de pruebas",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(200.0, 100.0, 100.0),
)


def make_load_unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-001",
        "name": "Caja normal",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def make_individual_extinguisher(nominal_kg: float = 3.0, **overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "EXT-IND",
        "name": "Extintor individual",
        "dimensions": Dimensions3D(60.0, 20.0, 20.0),
        "weight_kg": 4.0,
        "package_type": PackageType.INDIVIDUAL,
        "is_extinguisher": True,
        "extinguisher_agent": ExtinguisherAgent.PQS,
        "extinguisher_nominal_kg": nominal_kg,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def make_grouped_extinguisher(nominal_kg: float = 1.0, **overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "EXT-GRP",
        "name": "Extintores en caja grupal",
        "dimensions": Dimensions3D(50.0, 40.0, 30.0),
        "weight_kg": 12.0,
        "package_type": PackageType.GROUPED_BOX,
        "units_per_package": 10,
        "is_extinguisher": True,
        "extinguisher_agent": ExtinguisherAgent.PQS,
        "extinguisher_nominal_kg": nominal_kg,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]
