"""Fábricas compartidas para los tests de `cargo_optimizer.application`."""

from __future__ import annotations

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace

SMALL_SPACE = LoadingSpace(
    name="Furgón pequeño de pruebas",
    category=LoadingSpaceCategory.VAN,
    internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
)

LARGE_SPACE = LoadingSpace(
    name="Camión grande de pruebas",
    category=LoadingSpaceCategory.TRUCK,
    internal_dimensions=Dimensions3D(300.0, 200.0, 200.0),
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
