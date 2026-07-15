"""Construcción y filtrado barato de candidatos de colocación.

No duplica lógica geométrica ni de negocio: delega siempre en
`cargo_optimizer.geometry` (para la caja y el soporte) y en
`RulesEngine.evaluate_placement` (para la validez completa).
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.support import support_ratio as compute_support_ratio
from cargo_optimizer.optimization.models import CandidatePlacement, PhysicalLoadInstance
from cargo_optimizer.optimization.scoring import (
    bounding_volume_increment_cm3,
    local_residual_space_cm3,
    score_candidate,
)
from cargo_optimizer.rules.context import PlacementRuleContext
from cargo_optimizer.rules.engine import RulesEngine


def orientation_fits_loading_space(orientation: Orientation, loading_space: LoadingSpace) -> bool:
    """Filtro barato antes de evaluar reglas: descarta orientaciones que no caben desde el origen.

    Una comparación de extensiones, sin construir ningún candidato ni
    evaluar ninguna regla: si `orientation` no cabe en el espacio ni
    situándola en la esquina de origen, no cabrá en ninguna posición.
    No sustituye a `evaluate_bounds` (que sí comprueba la posición
    real): solo evita generar candidatos condenados de antemano.
    """
    dims = loading_space.internal_dimensions
    return (
        orientation.x_size_cm <= dims.length_cm
        and orientation.y_size_cm <= dims.width_cm
        and orientation.z_size_cm <= dims.height_cm
    )


def build_candidate(
    instance: PhysicalLoadInstance,
    position: Position3D,
    orientation: Orientation,
    orientation_order_index: int,
    loading_space: LoadingSpace,
    existing_placements: tuple[Placement, ...],
    existing_boxes: tuple[AxisAlignedBox, ...],
    load_units_by_id: Mapping[UUID, LoadUnit],
    rules_engine: RulesEngine,
    minimum_support_ratio: float,
    generation_index: int,
) -> CandidatePlacement:
    """Construye y evalúa un único candidato.

    No elige entre candidatos (eso es responsabilidad de la
    estrategia) ni duplica ninguna regla geométrica o de negocio: solo
    arma el `PlacementRuleContext` y delega en `RulesEngine`.
    `existing_boxes` se recibe ya calculado (una vez por instancia, no
    una vez por candidato) para no reconstruir la lista de cajas en
    cada llamada.
    """
    context = PlacementRuleContext(
        loading_space=loading_space,
        load_unit=instance.load_unit,
        candidate_position=position,
        candidate_orientation=orientation,
        existing_placements=existing_placements,
        load_units_by_id=load_units_by_id,
    )
    evaluation = rules_engine.evaluate_placement(
        context, minimum_support_ratio=minimum_support_ratio
    )

    candidate_box = AxisAlignedBox(position=position, dimensions=orientation.dimensions)
    support = compute_support_ratio(candidate_box, existing_boxes)
    volume_increment = bounding_volume_increment_cm3(
        existing_placements, candidate_box.max_x, candidate_box.max_y, candidate_box.max_z
    )
    residual = local_residual_space_cm3(
        loading_space, candidate_box.max_x, candidate_box.max_y, candidate_box.max_z
    )
    score = score_candidate(
        position.z_cm,
        position.x_cm,
        position.y_cm,
        support,
        volume_increment,
        residual,
        orientation_order_index,
        generation_index,
    )

    provisional_placement = Placement(
        load_unit_id=instance.load_unit.id,
        instance_number=instance.instance_number,
        position=position,
        orientation=orientation,
        sequence_number=generation_index + 1,
    )

    return CandidatePlacement(
        instance=instance,
        position=position,
        orientation=orientation,
        placement=provisional_placement,
        evaluation=evaluation,
        score=score,
        generation_index=generation_index,
    )
