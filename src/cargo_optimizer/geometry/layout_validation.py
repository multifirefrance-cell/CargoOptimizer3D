"""Validación geométrica de un layout completo de Placements.

No verifica peso máximo, reglas de extintores, apilamiento,
fragilidad, orientación permitida ni orden de descarga: esos controles
pertenecen al motor de restricciones (fase 3) y al motor de
optimización (fase 4). Aquí solo hay geometría.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.geometry.bounds import fits_inside_loading_space
from cargo_optimizer.geometry.box import box_from_placement
from cargo_optimizer.geometry.collision import find_overlapping_placements
from cargo_optimizer.geometry.support import is_supported


@dataclass(frozen=True, slots=True)
class LayoutValidationIssue:
    """Un problema geométrico concreto detectado en un layout."""

    code: str
    message: str
    placement_sequence_numbers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class LayoutValidationResult:
    """Resultado de validar un layout: válido o no, y la lista de problemas encontrados."""

    is_valid: bool
    issues: tuple[LayoutValidationIssue, ...]


def _find_out_of_bounds_issues(
    loading_space: LoadingSpace, placements: Sequence[Placement]
) -> list[LayoutValidationIssue]:
    issues: list[LayoutValidationIssue] = []
    for placement in placements:
        box = box_from_placement(placement)
        if not fits_inside_loading_space(box, loading_space):
            issues.append(
                LayoutValidationIssue(
                    code="OUT_OF_BOUNDS",
                    message=(
                        f"El Placement con sequence_number={placement.sequence_number} "
                        "queda fuera de los límites del Loading Space."
                    ),
                    placement_sequence_numbers=(placement.sequence_number,),
                )
            )
    return issues


def _find_overlap_issues(placements: Sequence[Placement]) -> list[LayoutValidationIssue]:
    return [
        LayoutValidationIssue(
            code="OVERLAP",
            message=(
                f"Los Placements con sequence_number={a.sequence_number} y "
                f"{b.sequence_number} se superponen."
            ),
            placement_sequence_numbers=(a.sequence_number, b.sequence_number),
        )
        for a, b in find_overlapping_placements(placements)
    ]


def _find_unsupported_issues(
    placements: Sequence[Placement], require_full_support: bool
) -> list[LayoutValidationIssue]:
    minimum_ratio = 1.0 if require_full_support else 0.0
    boxes = [box_from_placement(p) for p in placements]
    issues: list[LayoutValidationIssue] = []
    for placement, box in zip(placements, boxes, strict=True):
        other_boxes = [b for b in boxes if b is not box]
        if not is_supported(box, other_boxes, minimum_support_ratio=minimum_ratio):
            issues.append(
                LayoutValidationIssue(
                    code="UNSUPPORTED",
                    message=(
                        f"El Placement con sequence_number={placement.sequence_number} "
                        "no tiene suficiente soporte."
                    ),
                    placement_sequence_numbers=(placement.sequence_number,),
                )
            )
    return issues


def _find_duplicate_instance_number_issues(
    placements: Sequence[Placement],
) -> list[LayoutValidationIssue]:
    groups: dict[tuple[object, int], list[int]] = {}
    for placement in placements:
        key = (placement.load_unit_id, placement.instance_number)
        groups.setdefault(key, []).append(placement.sequence_number)

    issues: list[LayoutValidationIssue] = []
    for (load_unit_id, instance_number), sequence_numbers in groups.items():
        if len(sequence_numbers) > 1:
            issues.append(
                LayoutValidationIssue(
                    code="DUPLICATE_INSTANCE_NUMBER",
                    message=(
                        f"instance_number={instance_number} está duplicado para "
                        f"load_unit_id={load_unit_id} (sequence_numbers: {sequence_numbers})."
                    ),
                    placement_sequence_numbers=tuple(sequence_numbers),
                )
            )
    return issues


def _find_duplicate_sequence_number_issues(
    placements: Sequence[Placement],
) -> list[LayoutValidationIssue]:
    groups: dict[int, list[int]] = {}
    for placement in placements:
        groups.setdefault(placement.sequence_number, []).append(placement.sequence_number)

    issues: list[LayoutValidationIssue] = []
    for sequence_number, occurrences in groups.items():
        if len(occurrences) > 1:
            issues.append(
                LayoutValidationIssue(
                    code="DUPLICATE_SEQUENCE_NUMBER",
                    message=f"sequence_number={sequence_number} está duplicado.",
                    placement_sequence_numbers=tuple(occurrences),
                )
            )
    return issues


def validate_layout(
    loading_space: LoadingSpace,
    placements: Sequence[Placement],
    require_full_support: bool = True,
) -> LayoutValidationResult:
    """Valida un layout puramente en términos geométricos.

    Detecta: cajas fuera de límites, superposiciones, cajas sin
    soporte suficiente, `instance_number` duplicado para el mismo
    `load_unit_id`, y `sequence_number` duplicado. El resultado es
    determinista para una misma entrada.
    """
    issues: list[LayoutValidationIssue] = [
        *_find_out_of_bounds_issues(loading_space, placements),
        *_find_overlap_issues(placements),
        *_find_unsupported_issues(placements, require_full_support),
        *_find_duplicate_instance_number_issues(placements),
        *_find_duplicate_sequence_number_issues(placements),
    ]
    return LayoutValidationResult(is_valid=not issues, issues=tuple(issues))
