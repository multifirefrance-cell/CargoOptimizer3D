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
from cargo_optimizer.rules.codes import UNKNOWN_LOAD_UNIT_REFERENCE
from cargo_optimizer.rules.results import RuleEvaluation, RuleSeverity, RuleViolation


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

        Usado por `rules.stacking_rules` (soporte directo/transitivo,
        peso soportado) para no reconstruir la misma caja repetidas
        veces durante su propia recursión. Se construye una vez por
        evaluación de candidato (no por sub-llamada recursiva), a
        partir de `existing_boxes` — que ya es O(1) cuando el llamador
        proporciona `precomputed_existing_boxes`.
        """
        return dict(
            zip(
                (p.sequence_number for p in self.existing_placements),
                self.existing_boxes,
                strict=True,
            )
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
