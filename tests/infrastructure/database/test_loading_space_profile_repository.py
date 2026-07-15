"""Pruebas de `LoadingSpaceProfileRepository`: builtin, CRUD, protección, duplicado."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import (
    DuplicateLoadingSpaceProfileError,
    RecordNotFoundError,
    RepositoryError,
)
from cargo_optimizer.infrastructure.database.repositories import LoadingSpaceProfileRepository


def _space(**overrides: object) -> LoadingSpace:
    kwargs: dict[str, object] = {
        "name": "Bodega de prueba",
        "category": LoadingSpaceCategory.WAREHOUSE,
        "internal_dimensions": Dimensions3D(500.0, 300.0, 300.0),
    }
    kwargs.update(overrides)
    return LoadingSpace(**kwargs)  # type: ignore[arg-type]


def test_ensure_builtin_profiles_creates_the_three_standard_containers(
    db_manager: DatabaseManager,
) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    entries = repo.list_all()
    assert len(entries) == 3
    assert all(entry.is_builtin for entry in entries)
    names = {entry.loading_space.name for entry in entries}
    assert any("20 pies" in name for name in names)
    assert any("High Cube" in name for name in names)
    assert any("40 pies" in name and "High Cube" not in name for name in names)


def test_ensure_builtin_profiles_is_idempotent(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    repo.ensure_builtin_profiles()
    assert len(repo.list_all()) == 3


def test_add_and_get_by_id(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    added = repo.add(_space())
    assert repo.get_by_id(added.id) == added


def test_get_by_name_is_case_insensitive(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.add(_space(name="Camión rígido"))
    assert repo.get_by_name("camión rígido") is not None
    assert repo.get_by_name("CAMIÓN RÍGIDO") is not None
    assert repo.get_by_name("otro") is None


def test_list_active_orders_by_name(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.add(_space(name="Zeta"))
    repo.add(_space(name="Alfa"))
    repo.add(_space(name="Beta"))
    names = [entry.loading_space.name for entry in repo.list_all()]
    assert names == ["Alfa", "Beta", "Zeta"]


def test_search_matches_name_case_insensitive(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.add(_space(name="Camión rígido"))
    repo.add(_space(name="Semirremolque"))
    assert [s.name for s in repo.search("camión")] == ["Camión rígido"]
    assert repo.search("inexistente") == ()


def test_update_changes_fields(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    added = repo.add(_space(door_position=DoorPosition.REAR))
    updated = repo.update(
        LoadingSpace(
            id=added.id,
            name=added.name,
            category=added.category,
            internal_dimensions=added.internal_dimensions,
            door_position=DoorPosition.UNRESTRICTED,
            max_weight_kg=5000.0,
        )
    )
    assert updated.door_position == DoorPosition.UNRESTRICTED
    assert updated.max_weight_kg == 5000.0


def test_update_missing_record_raises(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    with pytest.raises(RecordNotFoundError):
        repo.update(_space())


def test_builtin_profile_cannot_be_updated_directly(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    builtin_entry = repo.list_all()[0]
    with pytest.raises(RepositoryError):
        repo.update(builtin_entry.loading_space)


def test_add_duplicate_name_raises(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.add(_space(name="Bodega X"))
    with pytest.raises(DuplicateLoadingSpaceProfileError):
        repo.add(_space(name="bodega x"))


def test_archive_then_restore(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    added = repo.add(_space())
    repo.archive(added.id)
    assert repo.get_by_name(added.name) is None
    repo.restore(added.id)
    assert repo.get_by_name(added.name) is not None


def test_duplicate_creates_independent_custom_copy(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    builtin_entry = repo.list_all()[0]
    copy = repo.duplicate(builtin_entry.loading_space.id, "Copia personalizada")
    assert copy.id != builtin_entry.loading_space.id
    assert copy.name == "Copia personalizada"
    copy_entry = next(e for e in repo.list_all() if e.loading_space.id == copy.id)
    assert copy_entry.is_builtin is False
    # La copia sí se puede actualizar directamente (no es builtin).
    repo.update(copy)


def test_max_weight_and_door_position_round_trip(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    added = repo.add(_space(max_weight_kg=12345.5, door_position=DoorPosition.LEFT))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.max_weight_kg == 12345.5
    assert fetched.door_position == DoorPosition.LEFT


def test_no_weight_limit_round_trips_as_none(db_manager: DatabaseManager) -> None:
    repo = LoadingSpaceProfileRepository(db_manager)
    added = repo.add(_space(max_weight_kg=None))
    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.max_weight_kg is None
