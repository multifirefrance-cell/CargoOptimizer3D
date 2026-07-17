"""Pruebas de `presentation_desktop_root()` (código fuente vs. build congelado con PyInstaller)."""

from __future__ import annotations

from pathlib import Path

import cargo_optimizer.presentation.desktop.paths as paths_module
from cargo_optimizer.presentation.desktop.paths import presentation_desktop_root


def test_resolves_to_file_parent_when_running_from_source(monkeypatch) -> None:
    monkeypatch.delattr(paths_module.sys, "_MEIPASS", raising=False)
    root = presentation_desktop_root()
    assert root == Path(paths_module.__file__).parent
    assert (root / "resources" / "icons").is_dir()


def test_resolves_under_meipass_when_running_frozen(monkeypatch, tmp_path) -> None:
    fake_bundle_root = tmp_path / "_MEIfake"
    monkeypatch.setattr(paths_module.sys, "_MEIPASS", str(fake_bundle_root), raising=False)
    root = presentation_desktop_root()
    assert root == fake_bundle_root / "cargo_optimizer" / "presentation" / "desktop"
