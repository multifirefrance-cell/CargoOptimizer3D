"""Contexto de evaluación para reglas de colocación.

`PlacementRuleContext` solo agrupa la información necesaria para
evaluar una colocación candidata; no decide ninguna regla por sí
mismo.

`precomputed_existing_boxes` (fase OPT-02, optimización de rendimiento
pura — ver `docs/OptimizerPerformance.md`) es un campo opcional para
que el llamador (siempre `optimization`, que ya mantiene
`PackingState.accepted_boxes` cacheado de forma incremental desde la
fase 4.2) evite que `existing_boxes` reconstruya la lista completa de
cajas con `box_from_placement` en cada acceso — antes se recalculaba
desde cero varias veces por candidato, sin usar el caché que
`optimization` ya calculaba y pasaba a `build_candidate` sin
aprovecharlo. Cuando no se proporciona (p. ej. en pruebas unitarias que
construyen un `PlacementRuleContext` directamente), el comportamiento
es exactamente el de antes: recalcular con `box_from_placement`. Mismo
resultado en ambos casos, nunca una aproximación.

`precomputed_spatial_index` (fase OPT-11, índice espacial — ver
`docs/OptimizerPerformance.md` y `geometry/spatial_index.py`) es, igual
que `precomputed_existing_boxes`, un campo opcional puramente aditivo:
`optimization.state.PackingState` mantiene un `SpatialIndex`
incremental y lo pasa aquí para que `rules` pueda restringir sus
recorridos O(n) de `existing_placements` (colisión, soporte,
apilamiento) a un superconjunto pequeño de candidatos cercanos, en vez
de recorrer siempre todos los placements existentes. Cuando no se
proporciona (`None`, el valor por defecto — el caso de toda prueba
unitaria que construye un `PlacementRuleContext` a mano), el
comportamiento es exactamente el de antes de esta fase: recorrer
`existing_placements` completo. Mismo resultado en ambos casos, nunca
una aproximación — el índice solo reduce cuántas comparaciones hacen
falta, nunca decide por sí mismo si hay colisión o soporte (ver
docstring de `SpatialIndex`).

`precomputed_box_by_sequence_number` (fase OPT-12, misma familia de
optimización pura de rendimiento — ver `docs/OptimizerPerformance.md`)
existe porque `box_by_sequence_number` se reconstruía por completo
(`dict(zip(...))`, O(n)) en **cada acceso**, y `evaluate_stack_count`
accede a él para el mismo candidato — una reconstrucción O(n)
redundante por candidato, sobre datos (`existing_placements`/
`existing_boxes`) que no cambian entre candidatos de la misma
instancia. `optimization` ya calcula `existing_boxes` una vez por
instancia (nunca por candidato); este campo permite construir el mapa
una sola vez en ese mismo punto y reutilizarlo para todos los
candidatos de esa instancia. Cuando no se proporciona (`None`), el
comportamiento es exactamente el de antes: reconstruir desde
`existing_boxes`/`existing_placements` en cada acceso. Mismo resultado
en ambos casos.

`precomputed_stack_level_by_sequence_number` (fase OPT-13, ver
`docs/OptimizerPerformance.md`) es el nivel de apilamiento ya conocido
de cada `Placement` existente, indexado por `sequence_number`.
`optimization.state.PackingState` lo mantiene de forma incremental (un
nivel calculado una única vez al aceptar cada `Placement`, nunca
recorriendo la cadena de soporte hacia arriba de forma recursiva — ver
`rules.stacking_rules`). Cuando no se proporciona (`None`, el caso de
toda prueba unitaria que construye un `PlacementRuleContext` a mano),
`stack_level_by_sequence_number` los calcula en una única pasada lineal
no recursiva (`compute_stack_levels`). Mismo resultado en ambos casos.

`precomputed_placement_by_sequence_number` (fase OPT-16, ver
`docs/OptimizerPerformance.md`) es la misma familia de caché
incremental que las anteriores, para `Placement` completos (no solo
sus cajas): `optimization.state.PackingState` lo mantiene añadiendo una
entrada por `Placement` aceptado. Existe porque `find_direct_supporting_placements`
(`rules.stack_levels`), al recibir un índice espacial, necesitaba
igualmente traducir el subconjunto barato de `sequence_number` cercanos
de vuelta a objetos `Placement` filtrando `existing_placements`
completo (`O(n)` por candidato pese al índice) — con este mapa, esa
traducción es `O(k)` sobre el subconjunto cercano. Cuando no se
proporciona (`None`), el comportamiento es exactamente el de antes:
filtrar `existing_placements` completo.

`precomputed_total_weight_kg` (fase OPT-16) es el peso bruto total ya
acumulado por los `Placement` existentes (`sum(unit.weight_kg for ...)`),
mantenido incrementalmente por `PackingState` en el mismo momento en
que acepta cada `Placement` — nunca una cifra de peso soportado por eje
ni por caja individual (eso sigue sin existir, ver ADR de la fase
OPT-13). Antes de esta fase, `rules.weight_rules.evaluate_loading_space_weight`
recorría `existing_placements` completo (`O(n)`) en cada candidato
evaluado para sumar este mismo total una y otra vez. Cuando no se
proporciona (`None`), el comportamiento es exactamente el de antes:
sumar `existing_placements` completo.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox, box_from_placement
from cargo_optimizer.geometry.spatial_index import SpatialIndex
from cargo_optimizer.rules.codes import UNKNOWN_LOAD_UNIT_REFERENCE
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation
from cargo_optimizer.rules.stack_levels import compute_stack_levels


@dataclass(frozen=True, slots=True)
class PlacementRuleContext:
    """Toda la información necesaria para evaluar una colocación candidata."""

    loading_space: LoadingSpace
    load_unit: LoadUnit
    candidate_position: Position3D
    candidate_orientation: Orientation
    existing_placements: tuple[Placement, ...]
    load_units_by_id: Mapping[UUID, LoadUnit]
    precomputed_existing_boxes: tuple[AxisAlignedBox, ...] | None = None
    precomputed_spatial_index: SpatialIndex | None = None
    precomputed_box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None
    precomputed_stack_level_by_sequence_number: Mapping[int, int] | None = None
    precomputed_placement_by_sequence_number: Mapping[int, Placement] | None = None
    precomputed_total_weight_kg: float | None = None

    @property
    def nearby_sequence_numbers(self) -> frozenset[int] | None:
        """Superconjunto barato de `sequence_number` cercanos a `candidate_box`, o `None`.

        `None` cuando no hay índice disponible — el llamador debe
        interpretarlo como "recorre `existing_placements` completo",
        nunca como "no hay nada cerca" (ver docstring del módulo).
        """
        if self.precomputed_spatial_index is None:
            return None
        return self.precomputed_spatial_index.query_box(self.candidate_box)

    @property
    def nearby_existing_boxes(self) -> tuple[AxisAlignedBox, ...]:
        """`existing_boxes`, filtradas a `nearby_sequence_numbers` cuando hay índice disponible.

        Sin índice (`nearby_sequence_numbers is None`), devuelve
        `existing_boxes` completo — idéntico al comportamiento anterior
        a esta fase. Usado por reglas que solo necesitan las cajas (no
        los `Placement`) para una comprobación geométrica sobre
        `candidate_box` sin recursión (soporte directo del candidato,
        nunca apilamiento/peso, que sí recorren distintas cajas
        candidatas en cada paso y necesitan volver a consultar el
        índice — ver `rules.stacking_rules`).

        Fase OPT-16: antes de esta fase, filtraba `existing_placements`
        completo (`O(n)`, ver `docs/OptimizerPerformance.md`) comparando
        cada `sequence_number` contra `nearby` uno a uno, pese a que
        `nearby` ya es el subconjunto pequeño que hacía falta — el
        índice espacial reducía cuántas cajas se comparaban
        geométricamente, pero no cuántas se recorrían para encontrarlas.
        Ahora traduce `nearby` directamente vía `box_by_sequence_number`
        (`O(k)`, `k = len(nearby)`), con el mismo resultado exacto.
        """
        nearby = self.nearby_sequence_numbers
        if nearby is None:
            return self.existing_boxes
        box_by_sequence_number = self.box_by_sequence_number
        return tuple(box_by_sequence_number[sequence_number] for sequence_number in nearby)

    @property
    def candidate_box(self) -> AxisAlignedBox:
        return AxisAlignedBox(
            position=self.candidate_position, dimensions=self.candidate_orientation.dimensions
        )

    @property
    def existing_boxes(self) -> tuple[AxisAlignedBox, ...]:
        if self.precomputed_existing_boxes is not None:
            return self.precomputed_existing_boxes
        return tuple(box_from_placement(p) for p in self.existing_placements)

    @property
    def box_by_sequence_number(self) -> Mapping[int, AxisAlignedBox]:
        """Cajas existentes indexadas por `Placement.sequence_number`, para búsqueda O(1).

        Usado por `rules.stacking_rules` (soporte directo) para no
        reconstruir la misma caja repetidas veces. Devuelve
        `precomputed_box_by_sequence_number` cuando el llamador lo
        proporciona (`optimization`, que lo calcula una única vez por
        instancia — ver docstring del módulo); si no, reconstruye desde
        `existing_boxes` exactamente como antes de esa optimización.
        """
        if self.precomputed_box_by_sequence_number is not None:
            return self.precomputed_box_by_sequence_number
        return dict(
            zip(
                (p.sequence_number for p in self.existing_placements),
                self.existing_boxes,
                strict=True,
            )
        )

    @property
    def stack_level_by_sequence_number(self) -> Mapping[int, int]:
        """Nivel de apilamiento ya conocido de cada `Placement`, indexado por `sequence_number`.

        Devuelve `precomputed_stack_level_by_sequence_number` cuando el
        llamador lo proporciona (`optimization.state.PackingState`, que
        lo mantiene incrementalmente — ver docstring del módulo); si
        no, lo calcula en una única pasada lineal, no recursiva
        (`rules.stack_levels.compute_stack_levels`).
        """
        if self.precomputed_stack_level_by_sequence_number is not None:
            return self.precomputed_stack_level_by_sequence_number
        return compute_stack_levels(
            self.existing_placements, self.box_by_sequence_number, self.precomputed_spatial_index
        )

    def load_unit_for_placement(self, placement: Placement) -> LoadUnit | None:
        return self.load_units_by_id.get(placement.load_unit_id)

    def validate_placement_references(self) -> RuleEvaluation:
        """Verifica que todo `existing_placements` referencie una LoadUnit conocida."""
        violations = tuple(
            RuleViolation(
                code=UNKNOWN_LOAD_UNIT_REFERENCE,
                message=(
                    f"El Placement con sequence_number={p.sequence_number} referencia "
                    f"load_unit_id={p.load_unit_id}, ausente en load_units_by_id."
                ),
                severity=RuleSeverity.ERROR,
                load_unit_id=p.load_unit_id,
                placement_sequence_numbers=(p.sequence_number,),
            )
            for p in self.existing_placements
            if p.load_unit_id not in self.load_units_by_id
        )
        if violations:
            return RuleEvaluation.rejected(violations)
        return RuleEvaluation.allowed()
