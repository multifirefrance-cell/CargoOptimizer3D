"""Puntuación determinista de candidatos.

El score es una tupla comparada lexicográficamente (se compara el
primer componente; solo si empata se mira el siguiente, y así
sucesivamente), nunca una suma ponderada: una suma exigiría calibrar
constantes arbitrarias entre magnitudes no comparables (cm frente a
cm³ frente a una ratio adimensional), es difícil de justificar y un
ajuste de peso puede reordenar resultados de forma silenciosa. El
orden lexicográfico no necesita calibración y es trivialmente
explicable ("A ganó porque su Z era menor"). Ver ADR-0009.

Componentes, en orden de prioridad:

1. menor z (posición vertical);
2. menor x;
3. menor y;
4. mayor `support_ratio` (negado, para que "mayor" siga ordenando ascendente);
5. menor incremento del bounding volume ocupado;
6. menor espacio residual local aproximado (heurística barata, no un
   cálculo real de espacio libre);
7. orden de orientación declarado por `RulesEngine` (favorece la
   orientación "natural", la primera en `allowed_orientation_codes`);
8. `generation_index`: desempate final, siempre determinista, nunca
   aleatorio.
"""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.placement import Placement


def bounding_dimensions(placements: Sequence[Placement]) -> tuple[float, float, float]:
    """Extensión máxima ocupada en cada eje por los placements dados; `(0, 0, 0)` si está vacío."""
    if not placements:
        return (0.0, 0.0, 0.0)
    return (
        max(p.max_x_cm for p in placements),
        max(p.max_y_cm for p in placements),
        max(p.max_z_cm for p in placements),
    )


def bounding_volume_cm3(placements: Sequence[Placement]) -> float:
    """Volumen de la caja envolvente de todos los placements dados. 0.0 si está vacío."""
    x, y, z = bounding_dimensions(placements)
    return x * y * z


def bounding_volume_increment_cm3(
    existing_placements: Sequence[Placement],
    candidate_max_x_cm: float,
    candidate_max_y_cm: float,
    candidate_max_z_cm: float,
) -> float:
    """Cuánto crecería el bounding volume actual si se acepta un candidato con estos máximos.

    No debe confundirse con el volumen realmente usado
    (`PackingResult.used_volume_cm3`, suma de volúmenes de cajas): esto
    es el volumen de la caja envolvente de todo el layout, que casi
    siempre es mayor que el volumen realmente ocupado.
    """
    current_volume = bounding_volume_cm3(existing_placements)
    existing_x, existing_y, existing_z = bounding_dimensions(existing_placements)
    new_x = max(existing_x, candidate_max_x_cm)
    new_y = max(existing_y, candidate_max_y_cm)
    new_z = max(existing_z, candidate_max_z_cm)
    return (new_x * new_y * new_z) - current_volume


def local_residual_space_cm3(
    loading_space: LoadingSpace,
    candidate_max_x_cm: float,
    candidate_max_y_cm: float,
    candidate_max_z_cm: float,
) -> float:
    """Aproximación barata del espacio "sobrante" entre el candidato y el fondo del Loading Space.

    No es un cálculo real de espacio libre (eso queda para una fase
    futura con partición espacial, ver docs/OptimizationEngineDesign.md):
    es solo el volumen de la caja entre el candidato y la esquina
    opuesta del espacio, usado como preferencia adicional de desempate
    hacia colocaciones que "llenan" más el espacio.
    """
    dims = loading_space.internal_dimensions
    residual_x = max(0.0, dims.length_cm - candidate_max_x_cm)
    residual_y = max(0.0, dims.width_cm - candidate_max_y_cm)
    residual_z = max(0.0, dims.height_cm - candidate_max_z_cm)
    return residual_x * residual_y * residual_z


def score_candidate(
    position_z_cm: float,
    position_x_cm: float,
    position_y_cm: float,
    support_ratio: float,
    bounding_volume_increment: float,
    residual_space: float,
    orientation_order_index: int,
    generation_index: int,
) -> tuple[float, float, float, float, float, float, int, int]:
    """Construye el score lexicográfico de un candidato. Cuanto menor, mejor."""
    return (
        position_z_cm,
        position_x_cm,
        position_y_cm,
        -support_ratio,
        bounding_volume_increment,
        residual_space,
        orientation_order_index,
        generation_index,
    )
