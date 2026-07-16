"""Pruebas de `MultiSpaceOptimizationWorker`: mismo patrón que `test_optimization_worker.py`.

`worker.run()` se llama directamente (sin `.start()`) donde solo hace
falta verificar señales y datos de forma síncrona y determinista — ver
el docstring de `test_optimization_worker.py` para la justificación
completa de este patrón.
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.models import MultiSpaceAssignmentRequest
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.workers.multi_space_optimization_worker import (
    MultiSpaceOptimizationWorker,
)


def _request(quantity: int = 5) -> MultiSpaceAssignmentRequest:
    space = LoadingSpace(
        name="Bodega de pruebas",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(500.0, 300.0, 300.0),
    )
    unit = LoadUnit(
        sku="WORKER-BOX",
        name="Caja de pruebas",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=10.0,
        quantity=quantity,
    )
    return MultiSpaceAssignmentRequest(loading_space_candidates=(space,), load_units=(unit,))


def test_run_emits_progress_and_finished_with_result(qapp: QApplication) -> None:
    worker = MultiSpaceOptimizationWorker(_request(quantity=5))
    progress_events: list[Any] = []
    results: list[Any] = []
    worker.progress.connect(progress_events.append)
    worker.optimization_finished.connect(results.append)

    worker.run()

    assert len(results) == 1
    result = results[0]
    assert result.total_requested_count == 5
    assert result.total_packed_count == 5
    assert result.stop_reason == MultiSpaceStopReason.ALL_PACKED
    assert result.spaces_used_count == 1


def test_pre_cancelled_token_produces_cancelled_stop_reason(qapp: QApplication) -> None:
    worker = MultiSpaceOptimizationWorker(_request(quantity=5))
    worker.cancellation_token.cancel()
    results: list[Any] = []
    worker.optimization_finished.connect(results.append)

    worker.run()

    assert len(results) == 1
    result = results[0]
    assert result.total_packed_count == 0
    assert result.stop_reason == MultiSpaceStopReason.CANCELLED
    assert len(result.final_unpacked_units) == 5


def test_run_emits_failed_signal_on_unexpected_exception(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = MultiSpaceOptimizationWorker(_request(quantity=1))

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("fallo simulado del motor multi-espacio")

    monkeypatch.setattr(
        "cargo_optimizer.presentation.desktop.workers.multi_space_optimization_worker."
        "MultiSpaceAssignmentEngine.assign",
        _boom,
    )
    failures: list[str] = []
    finished: list[Any] = []
    worker.optimization_failed.connect(failures.append)
    worker.optimization_finished.connect(finished.append)

    worker.run()

    assert failures == ["fallo simulado del motor multi-espacio"]
    assert finished == []


def test_starting_worker_does_not_block_caller(qapp: QApplication) -> None:
    worker = MultiSpaceOptimizationWorker(_request(quantity=15))
    results: list[Any] = []
    worker.optimization_finished.connect(results.append)

    worker.start()
    assert worker.isRunning()
    assert results == []

    finished = worker.wait(15000)
    assert finished, "El worker no terminó dentro del tiempo de espera"
    qapp.processEvents()
    assert len(results) == 1
    assert results[0].total_requested_count == 15
