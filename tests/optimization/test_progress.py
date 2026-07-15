"""Pruebas del callback de progreso.

Decisión documentada (ver docs/OptimizationEngine.md): una excepción
lanzada por el callback de progreso se convierte en una advertencia del
`PackingResult` y la ejecución continúa con normalidad — nunca
corrompe ni interrumpe el empaquetado.
"""

from __future__ import annotations

from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingProgress, PackingRequest
from tests.optimization._helpers import DEFAULT_SPACE, make_load_unit


def test_progress_called_at_start_and_end_and_per_instance() -> None:
    unit = make_load_unit(quantity=3)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))
    events: list[PackingProgress] = []
    engine = PackingEngine()

    result = engine.optimize(request, progress_callback=events.append)

    assert len(events) >= 2
    assert events[0].processed_instances == 0
    assert events[-1].packed_count == result.packed_count
    assert events[-1].processed_instances == result.packed_count + result.unpacked_count


def test_progress_callback_error_is_converted_to_warning() -> None:
    unit = make_load_unit(quantity=2)
    request = PackingRequest(loading_space=DEFAULT_SPACE, load_units=(unit,))

    def failing_callback(progress: PackingProgress) -> None:
        raise RuntimeError("boom")

    engine = PackingEngine()
    result = engine.optimize(request, progress_callback=failing_callback)

    assert result.packed_count == 2
    assert any("boom" in warning for warning in result.warnings)
