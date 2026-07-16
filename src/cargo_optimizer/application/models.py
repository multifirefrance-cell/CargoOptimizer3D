"""Tipos de datos inmutables del caso de uso de asignación multi-espacio.

Mismo estilo que `cargo_optimizer.optimization.models`
(`@dataclass(frozen=True, slots=True)`, ver ADR-0005): una
`MultiSpaceAssignmentRequest` de entrada, un `MultiSpaceAssignmentResult`
de salida, y un `MultiSpaceProgress` opcional para un callback de
avance. Ninguno de los tres reemplaza a `PackingRequest`/`PackingResult`
de `optimization`: los envuelve para orquestar varias ejecuciones de
`PackingEngine.optimize(...)`, una por `LoadingSpace` usado.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.exceptions import MultiSpaceAssignmentValidationError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.optimization.models import PackingRequest


@dataclass(frozen=True, slots=True)
class MultiSpaceAssignmentRequest:
    """Una solicitud completa e inmutable de asignación automática multi-espacio.

    `loading_space_candidates` es la lista de tipos de espacio que el
    usuario puso a disposición (el caso más común es una tupla de un
    solo elemento: "usa siempre contenedores de 40 pies"). Para cada
    espacio nuevo que haga falta, el motor ejecuta **todos** los
    candidatos y elige el mejor resultado de la ronda (más unidades
    cargadas, luego más volumen, luego más peso, luego menor capacidad
    del espacio; el orden de esta tupla solo actúa como desempate
    final) — ver `docs/MultiSpaceAssignment.md` para el criterio
    completo. Los demás campos son idénticos a `PackingRequest` y se
    aplican sin cambios a cada ejecución individual por espacio.
    """

    loading_space_candidates: tuple[LoadingSpace, ...]
    load_units: tuple[LoadUnit, ...]
    minimum_support_ratio: float = 1.0
    time_limit_seconds_per_space: float | None = None
    max_iterations_per_space: int | None = None
    max_spaces: int | None = None
    diagnostic_mode: bool = False

    def __post_init__(self) -> None:
        if not self.loading_space_candidates:
            raise MultiSpaceAssignmentValidationError(
                "loading_space_candidates no puede estar vacío: se necesita al menos "
                "un tipo de espacio candidato."
            )
        if not 0.0 <= self.minimum_support_ratio <= 1.0:
            raise MultiSpaceAssignmentValidationError(
                "minimum_support_ratio debe estar entre 0 y 1."
            )
        if self.time_limit_seconds_per_space is not None and self.time_limit_seconds_per_space <= 0:
            raise MultiSpaceAssignmentValidationError(
                "time_limit_seconds_per_space debe ser mayor que 0 cuando se especifica."
            )
        if self.max_iterations_per_space is not None and self.max_iterations_per_space <= 0:
            raise MultiSpaceAssignmentValidationError(
                "max_iterations_per_space debe ser mayor que 0 cuando se especifica."
            )
        if self.max_spaces is not None and self.max_spaces <= 0:
            raise MultiSpaceAssignmentValidationError(
                "max_spaces debe ser mayor que 0 cuando se especifica."
            )
        skus = [unit.sku for unit in self.load_units]
        if len(skus) != len(set(skus)):
            raise MultiSpaceAssignmentValidationError("Los SKU de load_units deben ser únicos.")
        unit_ids = [unit.id for unit in self.load_units]
        if len(unit_ids) != len(set(unit_ids)):
            raise MultiSpaceAssignmentValidationError("Los id de load_units deben ser únicos.")

    def build_space_request(
        self, loading_space: LoadingSpace, load_units: tuple[LoadUnit, ...]
    ) -> PackingRequest:
        """Construye la `PackingRequest` de un único espacio dentro de esta asignación."""
        return PackingRequest(
            loading_space=loading_space,
            load_units=load_units,
            minimum_support_ratio=self.minimum_support_ratio,
            time_limit_seconds=self.time_limit_seconds_per_space,
            max_iterations=self.max_iterations_per_space,
            diagnostic_mode=self.diagnostic_mode,
        )


@dataclass(frozen=True, slots=True)
class MultiSpaceProgress:
    """Instantánea inmutable de avance tras completar un espacio, para un callback opcional."""

    spaces_used: int
    current_space_index: int
    total_packed_so_far: int
    total_requested: int
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class MultiSpaceAssignmentResult:
    """Resultado completo de una asignación automática multi-espacio.

    `space_results` guarda un `PackingResult` por cada espacio
    realmente utilizado, en el orden en que se fue necesitando.
    `final_unpacked_units` son las instancias que, tras agotar todos
    los candidatos disponibles (o alcanzar `max_spaces`/la
    cancelación), quedaron definitivamente sin cargar — no confundir
    con `space_results[i].unpacked_units`, que en las rondas
    intermedias son solo "no cupo en *este* espacio todavía" y se
    reintentan en el siguiente.
    """

    space_results: tuple[PackingResult, ...]
    stop_reason: MultiSpaceStopReason
    total_requested_count: int
    total_packed_count: int
    final_unpacked_units: tuple[UnpackedUnit, ...]
    execution_time_seconds: float
    warnings: tuple[str, ...] = ()

    @property
    def spaces_used_count(self) -> int:
        return len(self.space_results)

    @property
    def is_fully_packed(self) -> bool:
        return self.stop_reason == MultiSpaceStopReason.ALL_PACKED and not self.final_unpacked_units

    @property
    def total_used_volume_cm3(self) -> float:
        return float(sum(result.used_volume_cm3 for result in self.space_results))

    @property
    def total_used_weight_kg(self) -> float:
        return float(sum(result.used_weight_kg for result in self.space_results))

    @property
    def total_capacity_volume_cm3(self) -> float:
        return float(sum(result.loading_space.capacity_volume_cm3 for result in self.space_results))

    @property
    def overall_volume_utilization_percent(self) -> float:
        capacity = self.total_capacity_volume_cm3
        if capacity <= 0:
            return 0.0
        return (self.total_used_volume_cm3 / capacity) * 100.0

    @property
    def overall_weight_utilization_percent(self) -> float | None:
        """`None` cuando ningún espacio usado declara `max_weight_kg`.

        Si algunos espacios usados declaran límite y otros no, el
        denominador solo suma los que sí lo declaran, mientras que el
        numerador (`total_used_weight_kg`) incluye el peso de todos los
        espacios usados — puede superar el 100% en ese caso mixto, lo
        cual es información honesta (no todo el peso cargado tiene un
        límite conocido contra el que compararse), no un error de
        cálculo.
        """
        total_max_weight_kg = sum(
            result.loading_space.max_weight_kg
            for result in self.space_results
            if result.loading_space.max_weight_kg is not None
        )
        if total_max_weight_kg <= 0:
            return None
        return (self.total_used_weight_kg / total_max_weight_kg) * 100.0

    @property
    def spaces_used_by_candidate_name(self) -> Mapping[str, int]:
        """Cuántos espacios usados corresponden a cada `LoadingSpace.name`.

        Se deriva de `space_results`, nunca se guarda por separado: el
        único dato nuevo aquí es el conteo agrupado, no una copia de
        qué espacio se usó en cada ronda (eso ya lo tiene cada
        `PackingResult.loading_space`).
        """
        counts: dict[str, int] = {}
        for result in self.space_results:
            name = result.loading_space.name
            counts[name] = counts.get(name, 0) + 1
        return MappingProxyType(counts)

    @property
    def average_volume_utilization_percent(self) -> float:
        if not self.space_results:
            return 0.0
        utilizations = [result.volume_utilization_percent for result in self.space_results]
        return sum(utilizations) / len(utilizations)

    @property
    def max_volume_utilization_percent(self) -> float:
        if not self.space_results:
            return 0.0
        return max(result.volume_utilization_percent for result in self.space_results)

    @property
    def min_volume_utilization_percent(self) -> float:
        if not self.space_results:
            return 0.0
        return min(result.volume_utilization_percent for result in self.space_results)

    @property
    def pending_count(self) -> int:
        """Cantidad total de instancias definitivamente sin cargar (`len(final_unpacked_units)`)."""
        return len(self.final_unpacked_units)
