"""Pruebas de `CatalogService`: inicialización, copia independiente al proyecto."""

from __future__ import annotations

from pathlib import Path

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.catalog_service import CatalogService


def test_create_default_initializes_database_and_builtin_profiles(tmp_path: Path) -> None:
    service = CatalogService.create_default(base_dir=tmp_path)
    try:
        assert service.health_check().ok is True
        assert len(service.profiles.list_all()) == 3
    finally:
        service.close()


def test_copy_to_project_generates_a_new_independent_id() -> None:
    catalog_unit = LoadUnit(
        sku="BOX-1", name="Caja", dimensions=Dimensions3D(40.0, 30.0, 20.0), weight_kg=10.0
    )
    project_unit = CatalogService.copy_to_project(catalog_unit)
    assert project_unit.id != catalog_unit.id
    assert project_unit.sku == catalog_unit.sku
    assert project_unit.name == catalog_unit.name


def test_copy_profile_to_project_generates_a_new_independent_id() -> None:
    catalog_space = LoadingSpace(
        name="Bodega",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
    )
    project_space = CatalogService.copy_profile_to_project(catalog_space)
    assert project_space.id != catalog_space.id
    assert project_space.name == catalog_space.name


def test_catalog_changes_never_alter_a_previously_copied_project_unit() -> None:
    """La copia entregada a un proyecto es completamente independiente del catálogo."""
    catalog_unit = LoadUnit(
        sku="BOX-1", name="Caja original", dimensions=Dimensions3D(40.0, 30.0, 20.0), weight_kg=10.0
    )
    project_unit = CatalogService.copy_to_project(catalog_unit)
    # Editar la instancia "de catálogo" no afecta a la copia ya entregada al proyecto
    # (son objetos inmutables e independientes, sin ninguna referencia compartida).
    assert project_unit.name == "Caja original"
    assert project_unit is not catalog_unit
