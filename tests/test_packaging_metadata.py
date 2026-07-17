"""Consistencia de metadatos de versión entre pyproject.toml, el paquete y el instalador.

No prueba el build de PyInstaller/Inno Setup en sí (eso exige el entorno
real de la fase de empaquetado, ver `scripts/build_windows_beta.bat`):
solo evita que una futura subida de versión olvide alguno de los tres
lugares donde el número aparece hoy — un error silencioso, ya que nada
más lo detectaría (ver `docs/ADR/ADR-0013-empaquetado-windows.md`).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import cargo_optimizer

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_pyproject_toml() -> None:
    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert cargo_optimizer.__version__ == pyproject["project"]["version"]


def test_pyinstaller_is_a_dev_only_dependency() -> None:
    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime_dependencies = pyproject["project"]["dependencies"]
    assert not any("pyinstaller" in dep.lower() for dep in runtime_dependencies)
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]
    assert any("pyinstaller" in dep.lower() for dep in dev_dependencies)


def test_installer_app_version_matches_package_version() -> None:
    installer_script = (_REPO_ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")
    match = re.search(r'#define MyAppVersion "([^"]+)"', installer_script)
    assert match is not None, "No se encontró MyAppVersion en packaging/installer.iss"
    assert match.group(1) == cargo_optimizer.__version__
