"""Estado mutable interno de una ejecución de `PackingEngine`.

Nunca se expone públicamente (no se exporta desde
`optimization/__init__.py`) ni se devuelve al llamador: se crea al
principio de `optimize()`, se pasa por referencia a la estrategia, y se
descarta tras construir el `PackingResult`. Toda mutación pasa por sus
métodos (`accept_placement`, `reject_instance`, `add_warning`); nadie
fuera de este objeto manipula listas internas directamente, así que no
puede quedar en un estado inconsistente (p. ej. reutilizar un número de
secuencia).

`packed_volume_cm3` y `packed_weight_kg` son propiedades derivadas de
`placements` en cada acceso, no totales acumulados en un campo aparte:
mantener un total "en vivo" además de la lista de placements sería una
segunda fuente de verdad que podría desincronizarse (ver ADR-0008 y
`docs/OptimizationEngineDesign.md`).

`_accepted_boxes` y `_bounding_max_*` sí son cachés incrementales
deliberadas (fase 4.2): a diferencia de `packed_volume_cm3`, mantenerlas
recalculadas desde cero en cada candidato evaluado (no solo en cada
instancia) fue el cuello de botella nº 1 medido por perfilado real
(ver `docs/PerformanceBaseline.md`) — `optimization/scoring.py`
recorría todos los placements aceptados por cada candidato, no por
instancia. Aquí sí hay una única fuente de verdad: se actualizan
exclusivamente dentro de `accept_placement`, en el mismo momento en que
`_placements` cambia, así que no pueden desincronizarse.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.optimization.models import CandidatePlacement, PhysicalLoadInstance


@dataclass(slots=True)
class PackingState:
    """Estado mutable de una única ejecución. No es parte de la API pública."""

    load_units_by_id: Mapping[UUID, LoadUnit]
    _placements: list[Placement] = field(default_factory=list)
    _unpacked: list[UnpackedUnit] = field(default_factory=list)
    _warnings: list[str] = field(default_factory=list)
    _sequence_counter: int = 0
    iteration_count: int = 0
    candidate_generation_count: int = 0
    _accepted_boxes: list[AxisAlignedBox] = field(default_factory=list)
    _bounding_max_x: float = 0.0
    _bounding_max_y: float = 0.0
    _bounding_max_z: float = 0.0

    @property
    def placements(self) -> tuple[Placement, ...]:
        return tuple(self._placements)

    @property
    def accepted_boxes(self) -> tuple[AxisAlignedBox, ...]:
        """Cajas de los placements aceptados, en el mismo orden, cacheadas incrementalmente."""
        return tuple(self._accepted_boxes)

    @property
    def bounding_dimensions(self) -> tuple[float, float, float]:
        """Extensión máxima ocupada en cada eje por los placements aceptados hasta ahora.

        Equivalente a `scoring.bounding_dimensions(self.placements)`, pero
        mantenido incrementalmente en O(1) por aceptación en vez de
        recorrer todos los placements en cada consulta.
        """
        return (self._bounding_max_x, self._bounding_max_y, self._bounding_max_z)

    @property
    def unpacked_units(self) -> tuple[UnpackedUnit, ...]:
        return tuple(self._unpacked)

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(self._warnings)

    @property
    def packed_load_unit_ids(self) -> tuple[UUID, ...]:
        return tuple(p.load_unit_id for p in self._placements)

    @property
    def packed_volume_cm3(self) -> float:
        return sum(p.volume_cm3 for p in self._placements)

    @property
    def packed_weight_kg(self) -> float:
        total = 0.0
        for placement in self._placements:
            unit = self.load_units_by_id.get(placement.load_unit_id)
            if unit is not None:
                total += unit.weight_kg
        return total

    def next_sequence_number(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter

    def accept_placement(self, candidate: CandidatePlacement) -> Placement:
        """Materializa el candidato como un `Placement` real, con número de secuencia definitivo."""
        placement = Placement(
            load_unit_id=candidate.instance.load_unit.id,
            instance_number=candidate.instance.instance_number,
            position=candidate.position,
            orientation=candidate.orientation,
            sequence_number=self.next_sequence_number(),
        )
        self._placements.append(placement)
        box = box_from_placement(placement)
        self._accepted_boxes.append(box)
        self._bounding_max_x = max(self._bounding_max_x, box.max_x)
        self._bounding_max_y = max(self._bounding_max_y, box.max_y)
        self._bounding_max_z = max(self._bounding_max_z, box.max_z)
        return placement

    def reject_instance(
        self, instance: PhysicalLoadInstance, reason_code: str, reason_message: str
    ) -> UnpackedUnit:
        unpacked = UnpackedUnit(
            load_unit_id=instance.load_unit.id,
            instance_number=instance.instance_number,
            reason_code=reason_code,
            reason_message=reason_message,
        )
        self._unpacked.append(unpacked)
        return unpacked

    def add_warning(self, message: str) -> None:
        self._warnings.append(message)

    def record_candidate_generated(self) -> None:
        self.candidate_generation_count += 1
