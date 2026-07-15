"""Pruebas de `ProjectHistoryRepository` y `PackingRunHistoryRepository`."""

from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.repositories import (
    PackingRunHistoryRepository,
    ProjectHistoryRepository,
)

_APP_VERSION = "0.11.0"


def _result(**overrides: object) -> PackingResult:
    space = LoadingSpace(
        name="Espacio de prueba",
        category=LoadingSpaceCategory.OTHER,
        internal_dimensions=Dimensions3D(100.0, 100.0, 100.0),
    )
    kwargs: dict[str, object] = {
        "loading_space": space,
        "placements": (),
        "unpacked_units": (),
        "requested_count": 5,
        "packed_count": 4,
        "used_volume_cm3": 1000.0,
        "used_weight_kg": 50.0,
        "execution_time_seconds": 1.5,
        "algorithm_name": "greedy_extreme_point_v1",
        "warnings": ("Aviso A", "Aviso B"),
    }
    kwargs.update(overrides)
    return PackingResult(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# ProjectHistoryRepository
# ---------------------------------------------------------------------


def test_record_open_creates_a_row(db_manager: DatabaseManager, tmp_path: Path) -> None:
    repo = ProjectHistoryRepository(db_manager)
    project_id = uuid4()
    path = tmp_path / "proyecto.cargo3d"
    path.touch()
    repo.record_open(
        project_id=project_id,
        project_name="proyecto",
        file_path=str(path),
        application_version=_APP_VERSION,
    )
    entries = repo.list_recent()
    assert len(entries) == 1
    assert entries[0].project_id == project_id
    assert entries[0].last_opened_at is not None
    assert entries[0].last_saved_at is None


def test_record_open_then_save_upserts_same_row(
    db_manager: DatabaseManager, tmp_path: Path
) -> None:
    repo = ProjectHistoryRepository(db_manager)
    project_id = uuid4()
    path = tmp_path / "proyecto.cargo3d"
    path.touch()

    repo.record_open(
        project_id=project_id,
        project_name="proyecto",
        file_path=str(path),
        application_version=_APP_VERSION,
    )
    repo.record_save(
        project_id=project_id,
        project_name="proyecto",
        file_path=str(path),
        application_version=_APP_VERSION,
        packed_count=4,
        requested_count=5,
        volume_utilization_percent=42.0,
        used_weight_kg=50.0,
        algorithm_name="greedy_extreme_point_v1",
    )

    entries = repo.list_recent()
    assert len(entries) == 1  # una sola fila por file_path, no dos
    assert entries[0].last_opened_at is not None
    assert entries[0].last_saved_at is not None
    assert entries[0].packed_count == 4
    assert entries[0].volume_utilization_percent == 42.0


def test_list_recent_respects_limit_and_order(db_manager: DatabaseManager, tmp_path: Path) -> None:
    repo = ProjectHistoryRepository(db_manager)
    for i in range(5):
        path = tmp_path / f"proyecto_{i}.cargo3d"
        path.touch()
        repo.record_open(
            project_id=uuid4(),
            project_name=f"proyecto_{i}",
            file_path=str(path),
            application_version=_APP_VERSION,
        )
    entries = repo.list_recent(limit=3)
    assert len(entries) == 3


def test_remove_missing_paths_deletes_only_nonexistent_files(
    db_manager: DatabaseManager, tmp_path: Path
) -> None:
    repo = ProjectHistoryRepository(db_manager)
    existing_path = tmp_path / "existe.cargo3d"
    existing_path.touch()
    missing_path = tmp_path / "no_existe.cargo3d"

    repo.record_open(
        project_id=uuid4(),
        project_name="existe",
        file_path=str(existing_path),
        application_version=_APP_VERSION,
    )
    repo.record_open(
        project_id=uuid4(),
        project_name="no_existe",
        file_path=str(missing_path),
        application_version=_APP_VERSION,
    )

    removed = repo.remove_missing_paths()
    assert removed == 1
    remaining = repo.list_recent()
    assert len(remaining) == 1
    assert remaining[0].file_path == str(existing_path)


def test_clear_removes_all_entries(db_manager: DatabaseManager, tmp_path: Path) -> None:
    repo = ProjectHistoryRepository(db_manager)
    path = tmp_path / "proyecto.cargo3d"
    path.touch()
    repo.record_open(
        project_id=uuid4(),
        project_name="proyecto",
        file_path=str(path),
        application_version=_APP_VERSION,
    )
    repo.clear()
    assert repo.list_recent() == ()


def test_project_without_a_file_path_is_not_supported_but_metrics_are_optional(
    db_manager: DatabaseManager, tmp_path: Path
) -> None:
    repo = ProjectHistoryRepository(db_manager)
    path = tmp_path / "sin_resultado.cargo3d"
    path.touch()
    repo.record_save(
        project_id=uuid4(),
        project_name="sin_resultado",
        file_path=str(path),
        application_version=_APP_VERSION,
    )
    entries = repo.list_recent()
    assert entries[0].packed_count is None
    assert entries[0].requested_count is None
    assert entries[0].algorithm_name is None


# ---------------------------------------------------------------------
# PackingRunHistoryRepository
# ---------------------------------------------------------------------


def test_record_run_creates_a_row_with_metrics(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_id = uuid4()
    repo.record_run(
        project_id=project_id,
        project_name="proyecto",
        result=_result(),
        application_version=_APP_VERSION,
    )
    entries = repo.list_for_project(project_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.project_id == project_id
    assert entry.requested_count == 5
    assert entry.packed_count == 4
    assert entry.warning_count == 2
    assert entry.algorithm_name == "greedy_extreme_point_v1"


def test_record_run_does_not_duplicate_full_result(db_manager: DatabaseManager) -> None:
    """No debe existir ninguna forma de recuperar los placements desde el historial."""
    repo = PackingRunHistoryRepository(db_manager)
    project_id = uuid4()
    repo.record_run(
        project_id=project_id,
        project_name="proyecto",
        result=_result(),
        application_version=_APP_VERSION,
    )
    entry = repo.list_for_project(project_id)[0]
    assert not hasattr(entry, "placements")
    assert not hasattr(entry, "unpacked_units")


def test_list_for_project_only_returns_that_project(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_a = uuid4()
    project_b = uuid4()
    repo.record_run(
        project_id=project_a, project_name="A", result=_result(), application_version=_APP_VERSION
    )
    repo.record_run(
        project_id=project_b, project_name="B", result=_result(), application_version=_APP_VERSION
    )
    entries_a = repo.list_for_project(project_a)
    assert len(entries_a) == 1
    assert entries_a[0].project_id == project_a


def test_list_recent_orders_newest_first(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_id = uuid4()
    repo.record_run(
        project_id=project_id,
        project_name="proyecto",
        result=_result(requested_count=1, packed_count=1),
        application_version=_APP_VERSION,
    )
    time.sleep(0.01)  # garantiza executed_at distinto entre ambas filas
    repo.record_run(
        project_id=project_id,
        project_name="proyecto",
        result=_result(requested_count=2, packed_count=2),
        application_version=_APP_VERSION,
    )
    entries = repo.list_recent(limit=10)
    assert len(entries) == 2
    # El más reciente (segundo insertado) aparece primero.
    assert entries[0].requested_count == 2


def test_list_for_project_respects_limit(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_id = uuid4()
    for _ in range(5):
        repo.record_run(
            project_id=project_id,
            project_name="proyecto",
            result=_result(),
            application_version=_APP_VERSION,
        )
    entries = repo.list_for_project(project_id, limit=2)
    assert len(entries) == 2


def test_clear_for_project_only_removes_that_project(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_a = uuid4()
    project_b = uuid4()
    repo.record_run(
        project_id=project_a, project_name="A", result=_result(), application_version=_APP_VERSION
    )
    repo.record_run(
        project_id=project_b, project_name="B", result=_result(), application_version=_APP_VERSION
    )
    repo.clear_for_project(project_a)
    assert repo.list_for_project(project_a) == ()
    assert len(repo.list_for_project(project_b)) == 1


def test_record_run_with_optional_file_path(db_manager: DatabaseManager) -> None:
    repo = PackingRunHistoryRepository(db_manager)
    project_id = uuid4()
    repo.record_run(
        project_id=project_id,
        project_name="proyecto",
        result=_result(),
        application_version=_APP_VERSION,
        project_file_path="C:/ruta/proyecto.cargo3d",
    )
    entry = repo.list_for_project(project_id)[0]
    assert entry.project_file_path == "C:/ruta/proyecto.cargo3d"
