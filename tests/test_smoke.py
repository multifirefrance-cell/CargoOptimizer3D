"""Pruebas de humo: el paquete se importa y la infraestructura básica funciona."""

from __future__ import annotations

import cargo_optimizer
import cargo_optimizer.application
import cargo_optimizer.domain
import cargo_optimizer.infrastructure
import cargo_optimizer.presentation
import cargo_optimizer.presentation.desktop


def test_version_is_defined() -> None:
    assert cargo_optimizer.__version__ == "0.2.0"


def test_all_layers_import() -> None:
    assert cargo_optimizer.domain is not None
    assert cargo_optimizer.application is not None
    assert cargo_optimizer.infrastructure is not None
    assert cargo_optimizer.presentation is not None
    assert cargo_optimizer.presentation.desktop is not None
