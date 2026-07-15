"""Poda segura de puntos candidatos.

Solo elimina un punto candidato cuando es geométricamente **cierto**
que ninguna orientación (de tamaño positivo) podrá producir jamás una
colocación válida en ese punto. Dos criterios, ambos absolutos:

1. El punto queda fuera de los límites del Loading Space en algún eje:
   como toda dimensión de orientación es estrictamente positiva
   (invariante de dominio), sumarla solo puede alejar aún más el
   candidato del límite, nunca acercarlo.
2. El punto queda estrictamente dentro del volumen interior de una
   caja ya existente (no en su superficie: tocar una cara no es poda,
   solo el interior estricto garantiza colisión). Como el punto es la
   esquina de origen del candidato, si ya está dentro de otra caja,
   cualquier caja construida a partir de él solapará esa caja.

Deliberadamente NO se poda por "punto dominado" (descartar un punto
porque otro candidato parece mejor en el score): eso sería una
heurística de optimización, no una certeza geométrica, y podría
descartar la única posición que en la práctica resulta válida tras
evaluar reglas no geométricas (peso, fragilidad, capacidad de
extintor, etc.). Ver `docs/OptimizerPerformance.md`.

Un punto podado nunca llega a `RulesEngine.evaluate_placement`, pero
`GreedyExtremePointStrategy` necesita saber igualmente qué código de
violación habría producido esa evaluación completa (`OUT_OF_BOUNDS` o
`COLLISION`, garantizados por construcción) para no alterar
`_classify_unpacked_reason`: un candidato podado por límites o
colisión SIEMPRE habría incluido ese código en su evaluación completa
(límites y colisión se evalúan siempre, nunca se omiten), así que
omitirlo del conjunto agregado de violaciones podría, en un caso límite,
hacer que el conjunto pareciera compuesto únicamente por
`LOADING_SPACE_WEIGHT_EXCEEDED` cuando en realidad no lo es. Por eso
`prune_candidate_positions` devuelve también los códigos garantizados
de los puntos podados.
"""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.geometry.box import AxisAlignedBox
from cargo_optimizer.geometry.constants import GEOMETRY_EPSILON_CM
from cargo_optimizer.rules.codes import COLLISION, OUT_OF_BOUNDS


def _is_outside_loading_space(position: Position3D, loading_space: LoadingSpace) -> bool:
    dims = loading_space.internal_dimensions
    return (
        position.x_cm >= dims.length_cm + GEOMETRY_EPSILON_CM
        or position.y_cm >= dims.width_cm + GEOMETRY_EPSILON_CM
        or position.z_cm >= dims.height_cm + GEOMETRY_EPSILON_CM
    )


def _is_strictly_inside_any_box(
    position: Position3D, existing_boxes: Sequence[AxisAlignedBox]
) -> bool:
    for box in existing_boxes:
        if (
            box.min_x + GEOMETRY_EPSILON_CM < position.x_cm < box.max_x - GEOMETRY_EPSILON_CM
            and box.min_y + GEOMETRY_EPSILON_CM < position.y_cm < box.max_y - GEOMETRY_EPSILON_CM
            and box.min_z + GEOMETRY_EPSILON_CM < position.z_cm < box.max_z - GEOMETRY_EPSILON_CM
        ):
            return True
    return False


def prune_candidate_positions(
    positions: Sequence[Position3D],
    loading_space: LoadingSpace,
    existing_boxes: Sequence[AxisAlignedBox],
) -> tuple[tuple[Position3D, ...], frozenset[str]]:
    """Elimina puntos candidatos que nunca podrán producir una colocación válida.

    Se aplica antes de multiplicar por las orientaciones factibles: podar
    un único punto aquí evita evaluar ese punto contra todas las
    orientaciones. No cambia qué candidato termina aceptado (los puntos
    podados jamás habrían sido aceptados de todos modos), solo cuántos se
    evalúan.

    Devuelve también el conjunto de códigos de violación garantizados
    por los puntos podados (`OUT_OF_BOUNDS`, `COLLISION`), para que el
    llamador los incorpore a su propio conjunto agregado de violaciones
    sin tener que evaluar el candidato completo.
    """
    kept: list[Position3D] = []
    pruned_codes: set[str] = set()
    for position in positions:
        if _is_outside_loading_space(position, loading_space):
            pruned_codes.add(OUT_OF_BOUNDS)
            continue
        if _is_strictly_inside_any_box(position, existing_boxes):
            pruned_codes.add(COLLISION)
            continue
        kept.append(position)
    return tuple(kept), frozenset(pruned_codes)
