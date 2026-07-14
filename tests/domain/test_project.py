"""Pruebas de CargoProject."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError, DuplicateSkuError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.project import CargoProject

_SPACE = LoadingSpace(
    name="Furgón",
    category=LoadingSpaceCategory.VAN,
    internal_dimensions=Dimensions3D(300.0, 180.0, 180.0),
)


def _unit(sku: str) -> LoadUnit:
    return LoadUnit(
        sku=sku,
        name=f"Unidad {sku}",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=10.0,
    )


def test_valid_project() -> None:
    project = CargoProject(
        name="Proyecto de prueba",
        loading_space=_SPACE,
        load_units=(_unit("A"), _unit("B")),
    )
    assert project.schema_version == "1.0"
    assert len(project.load_units) == 2


def test_empty_name_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        CargoProject(name="  ", loading_space=_SPACE)


def test_duplicate_sku_is_rejected() -> None:
    with pytest.raises(DuplicateSkuError):
        CargoProject(
            name="Proyecto con SKU duplicado",
            loading_space=_SPACE,
            load_units=(_unit("A"), _unit("A")),
        )


def test_empty_project_is_valid() -> None:
    project = CargoProject(name="Proyecto vacío", loading_space=_SPACE)
    assert project.load_units == ()
    assert project.latest_result is None
