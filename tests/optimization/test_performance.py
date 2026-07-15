"""Pruebas de rendimiento no frágiles: solo registran duración orientativa.

No fijan tiempos estrictos dependientes del equipo. El crecimiento real
medido (ver docs/OptimizationEngine.md, sección Rendimiento) es
marcadamente cúbico: ~0.1s para 10 cajas, ~5s para 50, ~35s para 100 en
la máquina de referencia usada al escribir esta fase — mucho más lento
de lo estimado en `docs/OptimizationEngineDesign.md` (fase 4.0, antes
de medir). Por eso la suite automática solo cubre 10/30/60 cajas
(unos segundos en total); 100/500 se documentan como benchmark manual,
no como parte de la suite normal, para no alargarla excesivamente (una
sola corrida de 500 cajas tarda del orden de una hora con este primer
algoritmo, sin índice espacial — exactamente el escenario que
`docs/OptimizationEngineDesign.md` ya advertía como no soportado en
v1).
"""

from __future__ import annotations

import time

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from tests.optimization._helpers import make_load_unit


def _run_and_time(quantity: int) -> tuple[float, int, int]:
    space = LoadingSpace(
        name="Espacio de benchmark",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(2000.0, 1000.0, 300.0),
    )
    unit = make_load_unit(dimensions=Dimensions3D(40.0, 30.0, 20.0), quantity=quantity)
    request = PackingRequest(loading_space=space, load_units=(unit,))

    start = time.monotonic()
    result = PackingEngine().optimize(request)
    elapsed = time.monotonic() - start
    return elapsed, result.packed_count, result.requested_count


@pytest.mark.parametrize("quantity", [10, 30, 60])
def test_benchmark_does_not_take_unreasonably_long(quantity: int) -> None:
    # Límite generoso (no un objetivo de rendimiento): detecta una regresión
    # catastrófica de complejidad, no exige una velocidad concreta. Cantidades
    # mayores (100, 500) se documentan como benchmark manual (ver
    # docs/OptimizationEngine.md) y no forman parte de la suite automática
    # porque, con este primer algoritmo sin índice espacial, tardan minutos u
    # horas — exactamente la limitación ya documentada, no un fallo del test.
    elapsed, packed_count, requested_count = _run_and_time(quantity)
    assert packed_count <= requested_count
    assert elapsed < 30.0
