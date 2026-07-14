"""Pruebas de LoadingSpace."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace


def test_valid_creation() -> None:
    space = LoadingSpace(
        name="Camión de prueba",
        category=LoadingSpaceCategory.TRUCK,
        internal_dimensions=Dimensions3D(600.0, 240.0, 260.0),
        door_position=DoorPosition.REAR,
        max_weight_kg=10_000.0,
    )
    assert space.name == "Camión de prueba"
    assert space.category is LoadingSpaceCategory.TRUCK


def test_empty_name_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        LoadingSpace(
            name="   ",
            category=LoadingSpaceCategory.TRUCK,
            internal_dimensions=Dimensions3D(600.0, 240.0, 260.0),
        )


@pytest.mark.parametrize("bad_weight", [0.0, -1.0])
def test_invalid_max_weight_is_rejected(bad_weight: float) -> None:
    with pytest.raises(DomainValidationError):
        LoadingSpace(
            name="Bodega",
            category=LoadingSpaceCategory.WAREHOUSE,
            internal_dimensions=Dimensions3D(600.0, 240.0, 260.0),
            max_weight_kg=bad_weight,
        )


def test_max_weight_none_is_allowed() -> None:
    space = LoadingSpace(
        name="Bodega sin límite de peso",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(600.0, 240.0, 260.0),
        max_weight_kg=None,
    )
    assert space.max_weight_kg is None


def test_capacity_volume() -> None:
    space = LoadingSpace(
        name="Rack",
        category=LoadingSpaceCategory.RACK,
        internal_dimensions=Dimensions3D(200.0, 100.0, 50.0),
    )
    assert space.capacity_volume_cm3 == 1_000_000.0
    assert space.capacity_volume_m3 == pytest.approx(1.0)


def test_predefined_profiles() -> None:
    c20 = LoadingSpace.standard_20ft_container()
    c40 = LoadingSpace.standard_40ft_container()
    c40hq = LoadingSpace.standard_40ft_high_cube_container()

    assert c20.category is LoadingSpaceCategory.CONTAINER
    assert c40.category is LoadingSpaceCategory.CONTAINER
    assert c40hq.category is LoadingSpaceCategory.CONTAINER
    # El contenedor 40 pies es más largo que el de 20 pies.
    assert c40.internal_dimensions.length_cm > c20.internal_dimensions.length_cm
    # El High Cube es más alto que el estándar de 40 pies.
    assert c40hq.internal_dimensions.height_cm > c40.internal_dimensions.height_cm


def test_categories_are_not_limited_to_containers() -> None:
    categories = {
        LoadingSpaceCategory.CONTAINER,
        LoadingSpaceCategory.TRUCK,
        LoadingSpaceCategory.VAN,
        LoadingSpaceCategory.TRAILER,
        LoadingSpaceCategory.WAREHOUSE,
        LoadingSpaceCategory.RACK,
        LoadingSpaceCategory.OTHER,
    }
    for category in categories:
        space = LoadingSpace(
            name=f"Espacio {category.value}",
            category=category,
            internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
        )
        assert space.category is category
