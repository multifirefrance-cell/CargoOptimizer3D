"""Estado mutable interno de una ejecución de `PackingEngine`.

Nunca se expone públicamente (no se exporta desde
`optimization/__init__.py`) ni se devuelve al llamador: se crea al
principio de `optimize()`, se pasa por referencia a la estrategia, y se
descarta tras construir el `PackingResult`. Toda mutación pasa por sus
métodos (`accept_placement`, `reject_instance`, `add_warning`); nadie
fuera de este objeto manipula listas internas directamente, así que no
puede quedar en un estado inconsistente (p. ej. reutilizar un número de
secuencia).

`packed_volume_cm3` sigue siendo una propiedad derivada de `placements`
en cada acceso (nunca se consulta dentro del bucle caliente de
candidatos, así que recalcularla no tiene impacto medible — ver
ADR-0008 y `docs/OptimizationEngineDesign.md`). `packed_weight_kg` deja
de serlo en la fase OPT-16 (ver `docs/OptimizerPerformance.md`): a
diferencia de `packed_volume_cm3`, el peso total sí se consulta por
candidato (indirectamente, vía `rules.weight_rules`), así que ahora es
un total incremental (`_packed_weight_kg`) actualizado exclusivamente
dentro de `accept_placement` — la misma única fuente de verdad que el
resto de cachés de este módulo, nunca un segundo cálculo paralelo que
pudiera desincronizarse.

`_accepted_boxes` y `_bounding_max_*` sí son cachés incrementales
deliberadas (fase 4.2): a diferencia de `packed_volume_cm3`, mantenerlas
recalculadas desde cero en cada candidato evaluado (no solo en cada
instancia) fue el cuello de botella nº 1 medido por perfilado real
(ver `docs/PerformanceBaseline.md`) — `optimization/scoring.py`
recorría todos los placements aceptados por cada candidato, no por
instancia. Aquí sí hay una única fuente de verdad: se actualizan
exclusivamente dentro de `accept_placement`, en el mismo momento en que
`_placements` cambia, así que no pueden desincronizarse.

`_spatial_index` (fase OPT-11, índice espacial — ver
`docs/OptimizerPerformance.md`) es la misma idea llevada a `rules`: un
`SpatialIndex` mantenido incrementalmente, insertando cada caja
aceptada exactamente una vez dentro de `accept_placement` (nunca
reconstruido desde cero), para que `rules` pueda restringir sus
comprobaciones de colisión/soporte/apilamiento a un superconjunto
pequeño de candidatos cercanos en vez de recorrer siempre todos los
placements existentes.

`_box_by_sequence_number` (fase OPT-12) es la misma familia de caché
incremental: antes, `PlacementRuleContext.box_by_sequence_number`
reconstruía este mismo mapa completo (`dict(zip(...))`, O(n)) en cada
acceso. Aquí se mantiene con una sola entrada añadida por aceptación
(O(1)), y se pasa ya construido a cada candidato de la misma
instancia — nunca se reconstruye desde cero salvo por la propia
mutación de este estado.

`_stack_level_by_sequence_number` (fase OPT-13, ver
`docs/OptimizerPerformance.md`) es la misma idea aplicada al nivel de
apilamiento: en vez de recorrer recursivamente la cadena de soporte en
cada evaluación de candidato (el diseño anterior a esta fase,
eliminado por completo, no solo optimizado), el nivel de cada
`Placement` se calcula **una única vez**, en el momento de aceptarlo,
a partir del nivel ya conocido de sus soportes directos — que, al
haberse aceptado antes, ya está en este mismo diccionario. Nunca hace
falta volver a subir por la cadena de soporte.

`_placement_by_sequence_number` y `_packed_weight_kg` (fase OPT-16, ver
`docs/OptimizerPerformance.md`) son la misma familia de caché
incremental: antes de esta fase, varias reglas (`evaluate_collision`,
`nearby_existing_boxes`, `find_direct_supporting_placements` desde
`evaluate_fragility`) traducían el subconjunto barato de
`sequence_number` que devuelve el índice espacial de vuelta a objetos
`Placement`/caja filtrando `existing_placements` completo (`O(n)` por
candidato, pese al índice), y `evaluate_loading_space_weight` sumaba el
peso de `existing_placements` completo en cada candidato. Ambas cachés
se actualizan exclusivamente dentro de `accept_placement`, igual que el
resto: `_placement_by_sequence_number` se rellena **después** de
calcular los soportes directos del propio `Placement` que se está
aceptando (para no incluirse a sí mismo como su propio soporte).

`cached_pruned_candidate_positions` (fase OPT-16) es una memoización,
no una caché incremental: `geometry.candidate_points.generate_candidate_positions`
+ `optimization.pruning.prune_candidate_positions` solo pueden cambiar
de resultado cuando cambia el conjunto de placements aceptados (es
decir, dentro de `accept_placement`), nunca entre dos intentos de
colocación consecutivos que no aceptan nada — dos instancias que fallan
seguidas (todo el resto de la ronda 2, o el final de la ronda 1 cuando
el espacio ya está lleno) recalculaban antes exactamente los mismos
puntos candidatos, letra por letra, sin que nada hubiera cambiado. Se
invalida comparando `len(_placements)` con el valor guardado en el
último cálculo — un contador de versión barato, sin necesitar
detectar qué cambió exactamente.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.geometry.candidate_points import generate_candidate_positions
from cargo_optimizer.geometry.spatial_index import SpatialIndex
from cargo_optimizer.optimization.models import CandidatePlacement, PhysicalLoadInstance
from cargo_optimizer.optimization.pruning import prune_candidate_positions
from cargo_optimizer.rules.stack_levels import find_direct_supporting_placements, stack_level_of


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
    _spatial_index: SpatialIndex = field(default_factory=SpatialIndex)
    _box_by_sequence_number: dict[int, AxisAlignedBox] = field(default_factory=dict)
    _stack_level_by_sequence_number: dict[int, int] = field(default_factory=dict)
    _placement_by_sequence_number: dict[int, Placement] = field(default_factory=dict)
    _packed_weight_kg: float = 0.0
    _cached_pruned_positions: tuple[Position3D, ...] = ()
    _cached_pruned_violation_codes: frozenset[str] = frozenset()
    _cache_placements_count: int = -1

    @property
    def placements(self) -> tuple[Placement, ...]:
        return tuple(self._placements)

    @property
    def accepted_boxes(self) -> tuple[AxisAlignedBox, ...]:
        """Cajas de los placements aceptados, en el mismo orden, cacheadas incrementalmente."""
        return tuple(self._accepted_boxes)

    @property
    def spatial_index(self) -> SpatialIndex:
        """Índice espacial de las cajas aceptadas hasta ahora, mantenido incrementalmente."""
        return self._spatial_index

    @property
    def box_by_sequence_number(self) -> Mapping[int, AxisAlignedBox]:
        """Cajas aceptadas indexadas por `sequence_number`, mantenido incrementalmente."""
        return self._box_by_sequence_number

    @property
    def stack_level_by_sequence_number(self) -> Mapping[int, int]:
        """Nivel de apilamiento de cada placement aceptado, mantenido incrementalmente."""
        return self._stack_level_by_sequence_number

    @property
    def placement_by_sequence_number(self) -> Mapping[int, Placement]:
        """Cada `Placement` aceptado indexado por `sequence_number`, mantenido incrementalmente."""
        return self._placement_by_sequence_number

    def cached_pruned_candidate_positions(
        self, loading_space: LoadingSpace
    ) -> tuple[tuple[Position3D, ...], frozenset[str]]:
        """Puntos candidatos ya podados, memoizados mientras no cambien los placements aceptados.

        Ver el docstring del módulo (fase OPT-16): dos intentos de
        colocación consecutivos sin ninguna aceptación de por medio
        (frecuente en la ronda 2, y al final de la ronda 1 cuando el
        espacio ya está lleno) producen exactamente el mismo resultado,
        así que se recalcula únicamente cuando `len(self._placements)`
        cambió desde el último cálculo.
        """
        if self._cache_placements_count != len(self._placements):
            raw_positions = generate_candidate_positions(self._placements)
            pruned_positions, pruned_violation_codes = prune_candidate_positions(
                raw_positions,
                loading_space,
                self._accepted_boxes,
                spatial_index=self._spatial_index,
                box_by_sequence_number=self._box_by_sequence_number,
            )
            self._cached_pruned_positions = pruned_positions
            self._cached_pruned_violation_codes = pruned_violation_codes
            self._cache_placements_count = len(self._placements)
        return self._cached_pruned_positions, self._cached_pruned_violation_codes

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
        """Peso bruto total ya aceptado, mantenido incrementalmente (fase OPT-16)."""
        return self._packed_weight_kg

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
        self._spatial_index.insert(placement.sequence_number, box)
        self._box_by_sequence_number[placement.sequence_number] = box
        supporters = find_direct_supporting_placements(
            box,
            self._placements[:-1],
            self._box_by_sequence_number,
            self._spatial_index,
            self._placement_by_sequence_number,
        )
        self._stack_level_by_sequence_number[placement.sequence_number] = stack_level_of(
            box, supporters, self._stack_level_by_sequence_number
        )
        # Se añade después de calcular `supporters`: `self` (el propio
        # placement que se está aceptando) nunca debe poder aparecer como
        # su propio soporte directo.
        self._placement_by_sequence_number[placement.sequence_number] = placement
        unit = self.load_units_by_id.get(placement.load_unit_id)
        if unit is not None:
            self._packed_weight_kg += unit.weight_kg
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
