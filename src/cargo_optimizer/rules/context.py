"""Contexto de evaluación para reglas de colocación.

`PlacementRuleContext` solo agrupa la información necesaria para
evaluar una colocación candidata; no decide ninguna regla por sí
mismo.
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

    @property
    def candidate_box(self) -> AxisAlignedBox:
        return AxisAlignedBox(
            position=self.candidate_position, dimensions=self.candidate_orientation.dimensions
        )

    @property
    def existing_boxes(self) -> tuple[AxisAlignedBox, ...]:
        return tuple(box_from_placement(p) for p in self.existing_placements)

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
