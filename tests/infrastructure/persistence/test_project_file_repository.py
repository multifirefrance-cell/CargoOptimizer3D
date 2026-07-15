"""Pruebas de `ProjectFileRepository`: round-trip, errores tipados, backups, atomicidad."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.project import CargoProject
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.infrastructure.persistence.exceptions import (
    ProjectFileCorruptError,
    ProjectFileNotFoundError,
    UnsupportedSchemaVersionError,
)
from cargo_optimizer.infrastructure.persistence.project_file_repository import (
    CURRENT_SCHEMA_VERSION,
    FORMAT_NAME,
    ProjectFileRepository,
)

_APP_VERSION = "0.10.0"


def _space() -> LoadingSpace:
    return LoadingSpace(
        name="Bodega de prueba",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
        door_position=DoorPosition.UNRESTRICTED,
        max_weight_kg=None,
        notes="Notas del espacio.",
    )


def _unit(sku: str = "BOX-1") -> LoadUnit:
    return LoadUnit(
        sku=sku,
        name="Caja de prueba",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=12.5,
        quantity=3,
        package_type=PackageType.INDIVIDUAL,
        notes="Notas de la caja.",
    )


def _result(unit: LoadUnit, space: LoadingSpace) -> PackingResult:
    orientation = Orientation.from_base_dimensions(
        unit.dimensions, unit.allowed_orientation_codes[0]
    )
    placement = Placement(
        load_unit_id=unit.id,
        instance_number=1,
        position=Position3D(0.0, 0.0, 0.0),
        orientation=orientation,
        sequence_number=1,
    )
    unpacked = UnpackedUnit(
        load_unit_id=unit.id,
        instance_number=2,
        reason_code="OUT_OF_SPACE",
        reason_message="No cupo en el espacio disponible.",
    )
    return PackingResult(
        loading_space=space,
        placements=(placement,),
        unpacked_units=(unpacked,),
        requested_count=3,
        packed_count=1,
        used_volume_cm3=24000.0,
        used_weight_kg=12.5,
        execution_time_seconds=0.42,
        algorithm_name="greedy_extreme_point_v1",
        warnings=("Aviso de prueba.",),
    )


def _project(with_result: bool = True) -> CargoProject:
    space = _space()
    unit = _unit()
    latest_result = _result(unit, space) if with_result else None
    return CargoProject(
        name="Proyecto de prueba",
        loading_space=space,
        load_units=(unit,),
        latest_result=latest_result,
        notes="Notas del proyecto.",
    )


def test_round_trip_preserves_the_full_project(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    project = _project()
    path = tmp_path / "proyecto.cargo3d"

    repo.save(project, path, application_version=_APP_VERSION)
    loaded = repo.load(path)

    assert loaded.project == project
    assert loaded.metadata.format_name == FORMAT_NAME
    assert loaded.metadata.schema_version == CURRENT_SCHEMA_VERSION
    assert loaded.metadata.application_version == _APP_VERSION


def test_round_trip_without_a_result_yet(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    project = _project(with_result=False)
    path = tmp_path / "proyecto_sin_resultado.cargo3d"

    repo.save(project, path, application_version=_APP_VERSION)
    loaded = repo.load(path)

    assert loaded.project.latest_result is None
    assert loaded.project == project


def test_saved_file_is_readable_utf8_json(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["format_name"] == FORMAT_NAME
    assert data["schema_version"] == CURRENT_SCHEMA_VERSION
    assert data["application_version"] == _APP_VERSION
    assert "created_at" in data
    assert "modified_at" in data
    assert "project" in data


def test_presentation_state_round_trips_as_an_opaque_blob(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    state = {"theme": "dark", "ui_state": {"splitters": {"main": "AAA="}}}

    repo.save(_project(), path, application_version=_APP_VERSION, presentation_state=state)
    loaded = repo.load(path)

    assert loaded.presentation_state == state


def test_created_at_is_preserved_across_saves(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    project = _project()

    first = repo.save(project, path, application_version=_APP_VERSION)
    second = repo.save(project, path, application_version=_APP_VERSION)

    assert first.created_at == second.created_at
    assert second.modified_at >= first.modified_at


def test_save_creates_a_backup_of_the_previous_version(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    backup_path = path.with_name(path.name + ".bak")

    repo.save(_project(with_result=False), path, application_version=_APP_VERSION)
    original_text = path.read_text(encoding="utf-8")
    assert not backup_path.exists()

    repo.save(_project(with_result=True), path, application_version=_APP_VERSION)

    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == original_text


def test_backup_of_a_nonexistent_file_is_a_no_op(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "no_existe.cargo3d"
    assert repo.backup(path) is None


def test_write_is_atomic_no_leftover_temp_files(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    leftover = [p for p in tmp_path.iterdir() if p.name.startswith(f".{path.name}.")]
    assert leftover == []
    assert path.exists()


def test_load_missing_file_raises_not_found(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    with pytest.raises(ProjectFileNotFoundError):
        repo.load(tmp_path / "no_existe.cargo3d")


def test_load_invalid_json_raises_corrupt_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupto.cargo3d"
    path.write_text("{ esto no es json valido ", encoding="utf-8")
    repo = ProjectFileRepository()
    with pytest.raises(ProjectFileCorruptError):
        repo.load(path)


def test_load_missing_required_fields_raises_corrupt_error(tmp_path: Path) -> None:
    path = tmp_path / "incompleto.cargo3d"
    path.write_text(json.dumps({"format_name": FORMAT_NAME}), encoding="utf-8")
    repo = ProjectFileRepository()
    with pytest.raises(ProjectFileCorruptError):
        repo.load(path)


def test_load_wrong_format_name_raises_corrupt_error(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "otro_formato.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["format_name"] = "otra_aplicacion_cualquiera"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ProjectFileCorruptError):
        repo.load(path)


def test_load_future_schema_version_raises_unsupported_error(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "futuro.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema_version"] = "99.0"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(UnsupportedSchemaVersionError):
        repo.load(path)


def test_load_project_with_corrupt_domain_data_raises_corrupt_error(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "dominio_invalido.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["project"]["load_units"][0]["weight_kg"] = -5.0  # domain rechaza pesos negativos
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ProjectFileCorruptError):
        repo.load(path)


def test_validate_checks_structure_without_reconstructing_the_project(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    path = tmp_path / "proyecto.cargo3d"
    repo.save(_project(), path, application_version=_APP_VERSION)

    metadata = repo.validate(path)
    assert metadata.format_name == FORMAT_NAME
    assert metadata.schema_version == CURRENT_SCHEMA_VERSION


def test_validate_missing_file_raises_not_found(tmp_path: Path) -> None:
    repo = ProjectFileRepository()
    with pytest.raises(ProjectFileNotFoundError):
        repo.validate(tmp_path / "no_existe.cargo3d")
