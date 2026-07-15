"""Esquema de columnas compartido para importar `LoadingSpace` desde Excel.

Usado por `loading_space_importer.py` y por `templates.py`
(`LoadingSpaceTemplate.xlsx`). Cubre cualquier espacio de carga
universal (contenedor, camión, van, bodega, espacio personalizado —
ver ADR-0002): `category` es solo metadata descriptiva, nunca se asume
que el archivo es específicamente de contenedores marítimos.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.excel.row_parsing import (
    RowConversionError,
    is_blank,
    parse_enum_label,
    parse_optional_float,
    parse_required_float,
)

LOADING_SPACE_SHEET_NAME = "Espacios de carga"

LOADING_SPACE_COLUMNS: tuple[str, ...] = (
    "Nombre",
    "Categoria",
    "Largo (cm)",
    "Ancho (cm)",
    "Alto (cm)",
    "Peso maximo (kg)",
    "Posicion de puerta",
    "Notas",
)

CATEGORY_LABELS: dict[LoadingSpaceCategory, str] = {
    LoadingSpaceCategory.CONTAINER: "Contenedor",
    LoadingSpaceCategory.TRUCK: "Camion",
    LoadingSpaceCategory.VAN: "Van",
    LoadingSpaceCategory.TRAILER: "Semirremolque",
    LoadingSpaceCategory.WAREHOUSE: "Bodega",
    LoadingSpaceCategory.RACK: "Rack",
    LoadingSpaceCategory.OTHER: "Otro",
}

DOOR_POSITION_LABELS: dict[DoorPosition, str] = {
    DoorPosition.FRONT: "Frontal",
    DoorPosition.REAR: "Trasera",
    DoorPosition.LEFT: "Izquierda",
    DoorPosition.RIGHT: "Derecha",
    DoorPosition.TOP: "Superior",
    DoorPosition.UNRESTRICTED: "Sin restriccion",
}


def loading_space_to_row(space: LoadingSpace) -> tuple[Any, ...]:
    """Traduce un `LoadingSpace` a una fila, en el mismo orden que `LOADING_SPACE_COLUMNS`."""
    return (
        space.name,
        CATEGORY_LABELS[space.category],
        space.internal_dimensions.length_cm,
        space.internal_dimensions.width_cm,
        space.internal_dimensions.height_cm,
        space.max_weight_kg,
        DOOR_POSITION_LABELS[space.door_position],
        space.notes,
    )


def row_to_loading_space(row_number: int, values: tuple[object, ...]) -> LoadingSpace:
    """Reconstruye un `LoadingSpace` a partir de una fila; valida completamente con el dominio."""
    (
        name_raw,
        category_raw,
        length_raw,
        width_raw,
        height_raw,
        max_weight_raw,
        door_raw,
        notes_raw,
    ) = values

    name = "" if name_raw is None else str(name_raw).strip()
    if not name:
        raise RowConversionError(row_number, "'Nombre' no puede estar vacío.")

    category = (
        LoadingSpaceCategory.OTHER
        if is_blank(category_raw)
        else parse_enum_label(
            CATEGORY_LABELS, category_raw, field_name="Categoria", row_number=row_number
        )
    )

    length_cm = parse_required_float(length_raw, field_name="Largo (cm)", row_number=row_number)
    width_cm = parse_required_float(width_raw, field_name="Ancho (cm)", row_number=row_number)
    height_cm = parse_required_float(height_raw, field_name="Alto (cm)", row_number=row_number)
    max_weight_kg = parse_optional_float(
        max_weight_raw, field_name="Peso maximo (kg)", row_number=row_number
    )

    door_position = (
        DoorPosition.REAR
        if is_blank(door_raw)
        else parse_enum_label(
            DOOR_POSITION_LABELS,
            door_raw,
            field_name="Posicion de puerta",
            row_number=row_number,
        )
    )
    notes = "" if notes_raw is None else str(notes_raw).strip()

    try:
        return LoadingSpace(
            id=uuid4(),
            name=name,
            category=category,
            internal_dimensions=Dimensions3D(length_cm, width_cm, height_cm),
            door_position=door_position,
            max_weight_kg=max_weight_kg,
            notes=notes,
        )
    except DomainValidationError as exc:
        raise RowConversionError(row_number, str(exc)) from exc
