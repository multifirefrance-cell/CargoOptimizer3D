"""Pruebas de `get_user_database_path`."""

from __future__ import annotations

from pathlib import Path

import pytest

from cargo_optimizer.infrastructure.database.paths import get_user_database_path


def test_get_user_database_path_with_base_dir(tmp_path: Path) -> None:
    path = get_user_database_path(base_dir=tmp_path)
    assert path.parent == tmp_path
    assert path.name == "cargo_optimizer.db"


def test_get_user_database_path_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir"
    assert not target.exists()
    path = get_user_database_path(base_dir=target)
    assert target.is_dir()
    assert path.parent == target


def test_get_user_database_path_without_base_dir_uses_local_app_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    path = get_user_database_path()
    assert path.parent.name == "CargoOptimizer3D"
    assert path.parent.parent == tmp_path
    assert path.parent.is_dir()
