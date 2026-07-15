"""Benchmark manual del motor de optimización (Fase 4.2).

Herramienta de desarrollo, no de producción ni de la suite de pytest:
genera escenarios deterministas de distintos tamaños y mide tiempo,
resultados y memoria aproximada. No requiere UI ni dependencias
externas (solo biblioteca estándar: `argparse`, `statistics`,
`time`, `tracemalloc`).

Uso:

    .venv\\Scripts\\python.exe scripts\\benchmark_optimizer.py --sizes 10 30 60 100
    .venv\\Scripts\\python.exe scripts\\benchmark_optimizer.py --sizes 250 500 --repeats 1

No se ejecuta como parte de `pytest` para tamaños grandes: ver
`tests/optimization/test_performance.py` para el benchmark automático
(acotado a tamaños pequeños para no alargar la suite normal).
"""

from __future__ import annotations

import argparse
import re
import statistics
import time
import tracemalloc
from collections.abc import Sequence

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import (
    ExtinguisherAgent,
    LoadingSpaceCategory,
    PackageType,
)
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest

_CANDIDATES_PATTERN = re.compile(r"candidates_generated=(\d+)")


def build_scenario(size: int) -> PackingRequest:
    """Escenario determinista: mezcla de SKU normales, extintor individual y caja grupal.

    El tamaño `size` reparte las instancias entre tres LoadUnit fijos,
    en las mismas proporciones para cualquier tamaño, de forma que el
    escenario crece de forma predecible y comparable entre tamaños.
    """
    space = LoadingSpace(
        name="Bodega de benchmark",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(2000.0, 1000.0, 300.0),
    )

    normal_qty = max(1, int(size * 0.8))
    extinguisher_qty = max(1, int(size * 0.1))
    grouped_qty = max(1, size - normal_qty - extinguisher_qty)

    normal_unit = LoadUnit(
        sku="BENCH-BOX",
        name="Caja de benchmark",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=10.0,
        quantity=normal_qty,
    )
    extinguisher_unit = LoadUnit(
        sku="BENCH-EXT-IND",
        name="Extintor individual de benchmark",
        dimensions=Dimensions3D(60.0, 20.0, 20.0),
        weight_kg=4.0,
        quantity=extinguisher_qty,
        package_type=PackageType.INDIVIDUAL,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.PQS,
        extinguisher_nominal_kg=5.0,
    )
    grouped_unit = LoadUnit(
        sku="BENCH-EXT-GRP",
        name="Caja grupal de extintores de benchmark",
        dimensions=Dimensions3D(50.0, 40.0, 30.0),
        weight_kg=12.0,
        quantity=grouped_qty,
        package_type=PackageType.GROUPED_BOX,
        units_per_package=10,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.PQS,
        extinguisher_nominal_kg=1.0,
    )

    return PackingRequest(
        loading_space=space,
        load_units=(normal_unit, extinguisher_unit, grouped_unit),
        diagnostic_mode=True,
    )


def _extract_candidates_generated(warnings: Sequence[str]) -> int | None:
    for warning in warnings:
        match = _CANDIDATES_PATTERN.search(warning)
        if match:
            return int(match.group(1))
    return None


def run_once(size: int) -> dict[str, object]:
    request = build_scenario(size)
    engine = PackingEngine()

    tracemalloc.start()
    start = time.perf_counter()
    result = engine.optimize(request)
    elapsed = time.perf_counter() - start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "elapsed_seconds": elapsed,
        "packed_count": result.packed_count,
        "unpacked_count": result.unpacked_count,
        "requested_count": result.requested_count,
        "candidates_generated": _extract_candidates_generated(result.warnings),
        "peak_memory_mb": peak / (1024 * 1024),
    }


def run_benchmark(sizes: Sequence[int], repeats: int) -> None:
    print(
        f"{'size':>6} {'median_s':>10} {'min_s':>8} {'max_s':>8} "
        f"{'packed':>8} {'unpacked':>9} {'candidates':>11} {'peak_MB':>9}"
    )
    for size in sizes:
        timings: list[float] = []
        last: dict[str, object] = {}
        for _ in range(repeats):
            last = run_once(size)
            timings.append(float(last["elapsed_seconds"]))
        median = statistics.median(timings)
        print(
            f"{size:>6} {median:>10.3f} {min(timings):>8.3f} {max(timings):>8.3f} "
            f"{last['packed_count']:>8} {last['unpacked_count']:>9} "
            f"{str(last['candidates_generated']):>11} {last['peak_memory_mb']:>9.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[10, 30, 60, 100],
        help="Cantidades de instancias a probar (por defecto: 10 30 60 100).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Repeticiones por tamaño, para reportar mediana/min/max (por defecto: 3).",
    )
    args = parser.parse_args()
    run_benchmark(args.sizes, args.repeats)


if __name__ == "__main__":
    main()
