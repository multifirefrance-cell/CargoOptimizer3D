"""Construcción y filtrado barato de candidatos de colocación.

No duplica lógica geométrica ni de negocio: delega siempre en
`cargo_optimizer.geometry` (para la caja y el soporte) y en
`RulesEngine.evaluate_placement` (para la validez completa).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.spatial_index import SpatialIndex
from cargo_optimizer.geometry.support import support_ratio as compute_support_ratio
from cargo_optimizer.optimization.models import CandidatePlacement, PhysicalLoadInstance
from cargo_optimizer.optimization.scoring import (
    bounding_volume_increment_from_dimensions,
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


def select_preferred_orientation(
    feasible_orientations: Sequence[tuple[int, Orientation]],
    loading_space: LoadingSpace,
) -> tuple[int, Orientation]:
    """Elige, entre las orientaciones factibles de un Load Unit, la que mejor tesela el piso.

    "Mejor tesela" = maximiza cuántas unidades caben en una sola capa
    repitiendo esa orientación en una rejilla regular
    (`floor(largo / x) * floor(ancho / y)`), no un cálculo real de
    aprovechamiento (no considera alturas ni espacio residual entre
    filas). Empate: se conserva la primera orientación en el orden ya
    declarado (`orientation_order_index` más bajo), igual que hace el
    resto del desempate de `score_candidate`.

    Todas las instancias de un mismo Load Unit fijan esta orientación
    como preferida (ver `GreedyExtremePointStrategy._process_instance`):
    intentarlas todas de forma independiente, instancia a instancia,
    permitía que el algoritmo alternara de orientación sin ningún
    criterio de conjunto, generando una geometría irregular (alturas de
    caja distintas en el mismo nivel) que fragmentaba los puntos
    candidatos generados para capas posteriores — el motivo raíz de los
    "muros"/columnas aisladas observados antes de esta fase (ver
    `docs/OptimizationEngine.md`). Solo se abandona esta orientación
    preferida, para una instancia concreta, cuando ninguna posición
    resulta válida con ella (fallback en `_process_instance`).
    """
    dims = loading_space.internal_dimensions
    best_index, best_orientation = feasible_orientations[0]
    best_capacity = -1
    for index, orientation in feasible_orientations:
        capacity = int(dims.length_cm // orientation.x_size_cm) * int(
            dims.width_cm // orientation.y_size_cm
        )
        if capacity > best_capacity:
            best_capacity = capacity
            best_index, best_orientation = index, orientation
    return best_index, best_orientation


_REJECTED_CANDIDATE_SCORE: tuple[float, float, float, float, float, float, int, int] = (
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0,
    0,
)


def build_candidate(
    instance: PhysicalLoadInstance,
    position: Position3D,
    orientation: Orientation,
    orientation_order_index: int,
    loading_space: LoadingSpace,
    existing_placements: tuple[Placement, ...],
    existing_boxes: tuple[AxisAlignedBox, ...],
    existing_bounding_dimensions: tuple[float, float, float],
    load_units_by_id: Mapping[UUID, LoadUnit],
    rules_engine: RulesEngine,
    minimum_support_ratio: float,
    generation_index: int,
    spatial_index: SpatialIndex | None = None,
    box_by_sequence_number: Mapping[int, AxisAlignedBox] | None = None,
    stack_level_by_sequence_number: Mapping[int, int] | None = None,
) -> CandidatePlacement:
    """Construye y evalúa un único candidato.

    No elige entre candidatos (eso es responsabilidad de la
    estrategia) ni duplica ninguna regla geométrica o de negocio: solo
    arma el `PlacementRuleContext` y delega en `RulesEngine`.
    `existing_boxes` y `existing_bounding_dimensions` se reciben ya
    calculados (una vez por instancia o mantenidos incrementalmente en
    `PackingState`, no una vez por candidato) para no reconstruirlos en
    cada llamada — el recálculo por candidato fue el cuello de botella
    nº 1 medido por perfilado real (ver `docs/PerformanceBaseline.md`).
    Desde la fase OPT-02, `existing_boxes` se pasa también a
    `PlacementRuleContext` (`precomputed_existing_boxes`): antes se
    calculaba aquí pero `rules` lo ignoraba por completo y volvía a
    reconstruir la lista completa de cajas desde cero en cada acceso a
    `context.existing_boxes` — varias veces por candidato, y de nuevo
    dentro de las reglas de apilamiento/peso soportado. Ver
    `docs/OptimizerPerformance.md`.

    Desde la fase OPT-12, `box_by_sequence_number` sigue el mismo
    patrón: quien llama (`GreedyExtremePointStrategy`, una vez por
    instancia, nunca por candidato) puede calcularlo y pasarlo aquí
    para que `PlacementRuleContext.box_by_sequence_number` no lo
    reconstruya (`dict(zip(...))`, O(n)) en cada acceso — antes
    `evaluate_stack_count` lo reconstruía para cada candidato.

    Desde la fase OPT-13, `stack_level_by_sequence_number` sigue el
    mismo patrón: `PackingState` lo mantiene incrementalmente (un nivel
    por `Placement` aceptado, calculado una única vez, sin recursión —
    ver `optimization/state.py`), y se pasa aquí para que
    `evaluate_stack_count` no tenga que recorrer la cadena de soporte.

    El *score* (soporte, incremento de bounding volume, espacio
    residual) solo se calcula si la colocación resulta permitida: un
    candidato rechazado nunca se compara por *score* (ver
    `GreedyExtremePointStrategy._process_instance`), así que calcularlo
    sería trabajo desperdiciado — y es, en concreto, la parte más cara
    de construir un candidato (soporte físico vía unión de rectángulos).
    """
    context = PlacementRuleContext(
        loading_space=loading_space,
        load_unit=instance.load_unit,
        candidate_position=position,
        candidate_orientation=orientation,
        existing_placements=existing_placements,
        load_units_by_id=load_units_by_id,
        precomputed_existing_boxes=existing_boxes,
        precomputed_spatial_index=spatial_index,
        precomputed_box_by_sequence_number=box_by_sequence_number,
        precomputed_stack_level_by_sequence_number=stack_level_by_sequence_number,
    )
    evaluation = rules_engine.evaluate_placement(
        context, minimum_support_ratio=minimum_support_ratio
    )

    candidate_box = AxisAlignedBox(position=position, dimensions=orientation.dimensions)

    if evaluation.is_allowed:
        support = compute_support_ratio(candidate_box, context.nearby_existing_boxes)
        volume_increment = bounding_volume_increment_from_dimensions(
            existing_bounding_dimensions,
            candidate_box.max_x,
            candidate_box.max_y,
            candidate_box.max_z,
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
    else:
        score = _REJECTED_CANDIDATE_SCORE

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
