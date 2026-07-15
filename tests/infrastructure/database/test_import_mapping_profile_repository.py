"""Pruebas de `ImportMappingProfileRepository`: CRUD, perfiles integrados, archivado (fase 8.1)."""

from __future__ import annotations

import uuid

import pytest

from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.exceptions import RecordNotFoundError, RepositoryError
from cargo_optimizer.infrastructure.database.repositories import ImportMappingProfileRepository


def test_add_and_get_by_id(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Mi perfil", "catalog", {"Código": "SKU"})

    fetched = repo.get_by_id(added.id)

    assert fetched is not None
    assert fetched.name == "Mi perfil"
    assert fetched.target_kind == "catalog"
    assert fetched.column_mapping == {"Código": "SKU"}
    assert fetched.is_builtin is False
    assert fetched.last_used_at is None


def test_get_by_name_is_case_insensitive(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.add("Kupfer", "catalog", {"Código": "SKU"})

    assert repo.get_by_name("kupfer") is not None
    assert repo.get_by_name("KUPFER") is not None
    assert repo.get_by_name("inexistente") is None


def test_add_duplicate_name_raises(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.add("Duplicado", "catalog", {})

    with pytest.raises(RepositoryError):
        repo.add("duplicado", "catalog", {})


def test_ensure_builtin_profiles_creates_four_official_profiles(
    db_manager: DatabaseManager,
) -> None:
    repo = ImportMappingProfileRepository(db_manager)

    repo.ensure_builtin_profiles()

    names = {entry.name for entry in repo.list_active()}
    assert names == {
        "Formato estándar CargoOptimizer",
        "Kupfer",
        "Joan",
        "Exanco",
    }
    assert all(entry.is_builtin for entry in repo.list_active())


def test_ensure_builtin_profiles_is_idempotent(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    repo.ensure_builtin_profiles()

    assert len(repo.list_active()) == 4


def test_list_active_filters_by_target_kind(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.add("Perfil catalogo", "catalog", {})
    repo.add("Perfil packing", "packing_list", {})

    assert [e.name for e in repo.list_active("catalog")] == ["Perfil catalogo"]
    assert [e.name for e in repo.list_active("packing_list")] == ["Perfil packing"]


def test_update_changes_name_and_mapping(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Original", "catalog", {"Código": "SKU"})

    updated = repo.update(added.id, name="Renombrado", column_mapping={"Ref": "SKU"})

    assert updated.name == "Renombrado"
    assert updated.column_mapping == {"Ref": "SKU"}


def test_update_missing_profile_raises(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)

    with pytest.raises(RecordNotFoundError):
        repo.update(uuid.uuid4(), name="X", column_mapping={})


def test_update_builtin_profile_raises(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    builtin = repo.get_by_name("Kupfer")
    assert builtin is not None

    with pytest.raises(RepositoryError):
        repo.update(builtin.id, name="Kupfer modificado", column_mapping={})


def test_archive_then_restore(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Perfil", "catalog", {})

    repo.archive(added.id)
    assert repo.get_by_name("Perfil") is None

    repo.restore(added.id)
    assert repo.get_by_name("Perfil") is not None


def test_archived_name_can_be_reused(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Perfil", "catalog", {})
    repo.archive(added.id)

    reused = repo.add("Perfil", "catalog", {"SKU": "SKU"})

    assert reused.name == "Perfil"


def test_duplicate_creates_independent_non_builtin_copy(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    repo.ensure_builtin_profiles()
    builtin = repo.get_by_name("Kupfer")
    assert builtin is not None

    copy = repo.duplicate(builtin.id, "Kupfer personalizado")

    assert copy.id != builtin.id
    assert copy.is_builtin is False
    assert copy.column_mapping == builtin.column_mapping


def test_touch_last_used_sets_timestamp(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Perfil", "catalog", {})
    assert added.last_used_at is None

    repo.touch_last_used(added.id)

    fetched = repo.get_by_id(added.id)
    assert fetched is not None
    assert fetched.last_used_at is not None


def test_list_all_includes_archived(db_manager: DatabaseManager) -> None:
    repo = ImportMappingProfileRepository(db_manager)
    added = repo.add("Perfil", "catalog", {})
    repo.archive(added.id)

    all_entries = repo.list_all()

    assert len(all_entries) == 1
    assert all_entries[0].is_active is False
