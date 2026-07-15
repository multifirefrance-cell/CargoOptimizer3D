"""Pruebas de `OptimizationWorker`: ejecución real de `PackingEngine`, cancelación, hilo.

`worker.run()` se llama directamente (sin `.start()`) en las pruebas que
solo necesitan verificar qué señales emite y con qué datos: ejecuta el
mismo código, en el hilo de la prueba, de forma síncrona y determinista
— sin condiciones de carrera de threading que hagan la prueba frágil.
La única prueba que sí usa `.start()` real (`test_starting_worker_does_not_block_caller`)
verifica precisamente la garantía de no bloqueo que exige usar un
`QThread` de verdad.
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.optimization.codes import UnpackedReason
from cargo_optimizer.optimization.models import PackingRequest
from cargo_optimizer.presentation.desktop.workers.optimization_worker import OptimizationWorker


def _request(quantity: int = 5) -> PackingRequest:
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
    return PackingRequest(loading_space=space, load_units=(unit,))


def test_run_emits_progress_and_finished_with_result(qapp: QApplication) -> None:
    worker = OptimizationWorker(_request(quantity=5))
    progress_events: list[Any] = []
    results: list[Any] = []
    worker.progress.connect(progress_events.append)
    worker.optimization_finished.connect(results.append)

    worker.run()

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, PackingResult)
    assert result.requested_count == 5
    assert result.packed_count == 5
    assert len(progress_events) >= 2
    assert progress_events[0].total_instances == 5


def test_pre_cancelled_token_produces_all_units_unpacked_deterministically(
    qapp: QApplication,
) -> None:
    worker = OptimizationWorker(_request(quantity=5))
    worker.cancellation_token.cancel()
    results: list[Any] = []
    worker.optimization_finished.connect(results.append)

    worker.run()

    assert len(results) == 1
    result = results[0]
    assert result.packed_count == 0
    assert len(result.unpacked_units) == 5
    for unpacked in result.unpacked_units:
        assert unpacked.reason_code == UnpackedReason.CANCELLED.value


def test_run_emits_failed_signal_on_unexpected_exception(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = OptimizationWorker(_request(quantity=1))

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("fallo simulado del motor")

    monkeypatch.setattr(
        "cargo_optimizer.presentation.desktop.workers.optimization_worker.PackingEngine.optimize",
        _boom,
    )
    failures: list[str] = []
    finished: list[Any] = []
    worker.optimization_failed.connect(failures.append)
    worker.optimization_finished.connect(finished.append)

    worker.run()

    assert failures == ["fallo simulado del motor"]
    assert finished == []


def test_starting_worker_does_not_block_caller(qapp: QApplication) -> None:
    # Cantidad pequeña deliberada: el motor real es O(n^3)-ish (ver
    # docs/OptimizerPerformance.md), así que una cantidad grande haría esta
    # prueba lenta sin aportar nada — probar que start() no bloquea no exige
    # una tarea larga, solo una tarea que tarde más que "cero" en terminar.
    worker = OptimizationWorker(_request(quantity=15))
    results: list[Any] = []
    worker.optimization_finished.connect(results.append)

    worker.start()
    # Si start() bloqueara hasta terminar, 'results' ya tendría un elemento aquí.
    assert worker.isRunning()
    assert results == []

    finished = worker.wait(15000)
    assert finished, "El worker no terminó dentro del tiempo de espera"
    qapp.processEvents()  # entrega la señal en cola al hilo de la prueba
    assert len(results) == 1
    assert results[0].requested_count == 15
