"""Pruebas de humo: el paquete se importa y el SDK público funciona."""

from __future__ import annotations

import cargo_optimizer
import cargo_optimizer.application
import cargo_optimizer.domain
import cargo_optimizer.geometry
import cargo_optimizer.infrastructure
import cargo_optimizer.optimization
import cargo_optimizer.presentation
import cargo_optimizer.presentation.desktop
import cargo_optimizer.rules
from cargo_optimizer import LoadingSpace, LoadUnit, PackingEngine, PackingRequest


def test_version_is_defined() -> None:
    assert cargo_optimizer.__version__ == "0.16.0"


def test_all_layers_import() -> None:
    assert cargo_optimizer.domain is not None
    assert cargo_optimizer.geometry is not None
    assert cargo_optimizer.rules is not None
    assert cargo_optimizer.optimization is not None
    assert cargo_optimizer.application is not None
    assert cargo_optimizer.infrastructure is not None
    assert cargo_optimizer.presentation is not None
    assert cargo_optimizer.presentation.desktop is not None


def test_public_sdk_exports_domain_model() -> None:
    assert LoadingSpace is cargo_optimizer.domain.LoadingSpace
    assert LoadUnit is cargo_optimizer.domain.LoadUnit


def test_public_sdk_exports_optimization_engine() -> None:
    assert PackingEngine is cargo_optimizer.optimization.PackingEngine
    assert PackingRequest is cargo_optimizer.optimization.PackingRequest
