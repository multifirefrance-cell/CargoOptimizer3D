"""Exportación avanzada de un `PackingResult` (fase 8.1): hojas, orden, nombres, ocultar vacías.

Construye el mismo libro de 5 hojas que `result_exporter.py` (nunca
duplica la construcción de cada hoja) y luego elige, reordena, renombra
y opcionalmente oculta las hojas vacías directamente sobre ese mismo
`Workbook` — sin copiar celdas entre libros.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.infrastructure.excel.exceptions import ExcelError
from cargo_optimizer.infrastructure.excel.result_exporter import (
    SHEET_PACKED,
    SHEET_SPACE,
    SHEET_SUMMARY,
    SHEET_UNPACKED,
    SHEET_WARNINGS,
    build_packing_result_workbook,
)
from cargo_optimizer.infrastructure.excel.workbook_utils import save_workbook_atomic


@dataclass(frozen=True, slots=True)
class SheetSelection:
    """Una hoja a incluir en una exportación avanzada: qué hoja, en qué orden, con qué nombre."""

    canonical_name: str
    display_name: str | None = None

    @property
    def resolved_name(self) -> str:
        return self.display_name if self.display_name else self.canonical_name


def default_sheet_order() -> tuple[str, ...]:
    """El orden con el que `export_packing_result` genera las cinco hojas."""
    return (SHEET_SUMMARY, SHEET_PACKED, SHEET_UNPACKED, SHEET_WARNINGS, SHEET_SPACE)


def is_sheet_empty(canonical_name: str, result: PackingResult) -> bool:
    """Resumen y Datos del espacio nunca se consideran vacíos; las demás, según su contenido."""
    if canonical_name == SHEET_PACKED:
        return not result.placements
    if canonical_name == SHEET_UNPACKED:
        return not result.unpacked_units
    if canonical_name == SHEET_WARNINGS:
        return not result.warnings
    return False


def export_packing_result_advanced(
    result: PackingResult,
    load_units_by_id: Mapping[UUID, LoadUnit],
    path: Path,
    *,
    application_version: str,
    sheet_selections: Sequence[SheetSelection] | None = None,
    hide_empty_sheets: bool = False,
) -> None:
    """Exporta `result`, permitiendo elegir hojas, su orden, su nombre y ocultar las vacías.

    ``sheet_selections`` por defecto incluye las cinco hojas en su
    orden habitual. Lanza `ExcelError` si, tras filtrar, no queda
    ninguna hoja que exportar.
    """
    workbook = build_packing_result_workbook(
        result, load_units_by_id, application_version=application_version
    )

    selections = (
        list(sheet_selections)
        if sheet_selections is not None
        else [SheetSelection(name) for name in default_sheet_order()]
    )
    if hide_empty_sheets:
        selections = [s for s in selections if not is_sheet_empty(s.canonical_name, result)]
    if not selections:
        raise ExcelError("La exportación avanzada no incluye ninguna hoja.")

    chosen_canonical_names = {selection.canonical_name for selection in selections}
    for existing_name in list(workbook.sheetnames):
        if existing_name not in chosen_canonical_names:
            workbook.remove(workbook[existing_name])

    ordered_titles: list[str] = []
    for selection in selections:
        worksheet = workbook[selection.canonical_name]
        worksheet.title = selection.resolved_name
        ordered_titles.append(selection.resolved_name)

    # openpyxl no expone una API pública para fijar el orden completo de las
    # hojas de una vez (solo `move_sheet`, que mueve una hoja por desplazamiento
    # relativo) — `_sheets` es la lista interna que ya usan varias recetas
    # documentadas de la comunidad para reordenar en un solo paso.
    workbook._sheets = [workbook[title] for title in ordered_titles]  # type: ignore[attr-defined]
    workbook.active = 0

    save_workbook_atomic(workbook, path)
