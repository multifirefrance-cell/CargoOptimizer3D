"""Pruebas de humo: el paquete se importa y la infraestructura básica funciona."""

from __future__ import annotations

import cargo_optimizer
import cargo_optimizer.core
import cargo_optimizer.ui


def test_version_is_defined() -> None:
    assert cargo_optimizer.__version__ == "0.1.0"


def test_core_and_ui_packages_import() -> None:
    assert cargo_optimizer.core is not None
    assert cargo_optimizer.ui is not None
