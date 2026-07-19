"""Esquema de columnas compartido para importar/exportar `LoadUnit` desde Excel.

Usado tanto por `catalog_importer.py`/`catalog_exporter.py` (catálogo
completo) como por `templates.py` (`CatalogTemplate.xlsx`). Las
etiquetas en español (tipo de empaque, agente extintor, orientación)
son una copia deliberada e independiente de las que ya existen en
`presentation/desktop/dialogs/catalog_product_editor_dialog.py`: son un
concepto distinto (texto de celda de una hoja de cálculo, no items de
un `QComboBox`) y `infrastructure` nunca puede importar de
`presentation`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any
from uuid import uuid4

from cargo_optimizer.domain.color_suggestions import suggest_pastel_color
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import (
    DEFAULT_MAX_STACK_COUNT,
    DEFAULT_ORIENTATION_CODES,
    LoadUnit,
)
from cargo_optimizer.infrastructure.excel.row_parsing import (
    RowConversionError,
    format_bool,
    is_blank,
    parse_bool,
    parse_enum_label,
    parse_int,
    parse_optional_float,
    parse_required_float,
)

CATALOG_SHEET_NAME = "Catálogo"

EXAMPLE_ROW_SKU_MARKER = "EJEMPLO-PLANTILLA-BORRAR-ESTA-FILA"
"""SKU reservado de la fila de ejemplo en la plantilla oficial descargable (fase OPT-18).

Ningún SKU real de un usuario coincidirá con este texto por accidente.
`import_catalog_from_worksheet` reconoce esta fila y la omite en
silencio (ni se importa ni se cuenta como error), así que la fila de
ejemplo de `generate_product_import_template` nunca puede colarse como
un producto real, aunque el usuario olvide borrarla antes de importar.
"""

PRODUCT_COLUMNS: tuple[str, ...] = (
    "SKU",
    "Nombre",
    "Largo (cm)",
    "Ancho (cm)",
    "Alto (cm)",
    "Peso (kg)",
    "Cantidad",
    "Color",
    "Fragil",
    "Tipo de empaque",
    "Extintor",
    "Agente",
    "Peso nominal (kg)",
    "Apilamiento",
    "Orientaciones",
    "Notas",
)

PACKAGE_TYPE_LABELS: dict[PackageType, str] = {
    PackageType.INDIVIDUAL: "Individual",
    PackageType.GROUPED_BOX: "Caja grupal",
    PackageType.PALLET: "Pallet",
    PackageType.DRUM: "Tambor",
    PackageType.CYLINDER: "Cilindro",
    PackageType.IRREGULAR_BOUNDING_BOX: "Carga irregular",
    PackageType.OTHER: "Otro",
}

EXTINGUISHER_AGENT_LABELS: dict[ExtinguisherAgent, str] = {
    ExtinguisherAgent.PQS: "PQS",
    ExtinguisherAgent.CO2: "CO2",
    ExtinguisherAgent.WATER: "Agua",
    ExtinguisherAgent.FOAM: "Espuma",
    ExtinguisherAgent.WET_CHEMICAL: "Quimico humedo",
    ExtinguisherAgent.CLEAN_AGENT: "Agente limpio",
    ExtinguisherAgent.OTHER: "Otro",
    ExtinguisherAgent.NOT_APPLICABLE: "No aplica",
}

ORIENTATION_LABELS: dict[OrientationCode, str] = {
    OrientationCode.LWH_XYZ: "Original",
    OrientationCode.WLH_XYZ: "Girada 90 Z",
    OrientationCode.LHW_XYZ: "Girada 90 X",
    OrientationCode.HWL_XYZ: "Girada 90 Y",
    OrientationCode.WHL_XYZ: "Ancho-alto-largo",
    OrientationCode.HLW_XYZ: "Alto-largo-ancho",
}

_ALL_ORIENTATIONS_LABEL = "Todas"


def _label_for(mapping: Mapping[Any, str], value: object) -> str:
    return mapping[value]


def _parse_orientations(raw: object, *, row_number: int) -> tuple[OrientationCode, ...]:
    """Celda vacía (producto nuevo sin configurar) -> `DEFAULT_ORIENTATION_CODES` (fase
    OPT-17), nunca las 6. Una celda con el texto explícito "Todas" sigue significando
    las 6 tal cual — es una elección explícita del usuario/exportación anterior, no un
    valor por defecto silencioso."""
    if is_blank(raw):
        return DEFAULT_ORIENTATION_CODES
    if str(raw).strip().casefold() == _ALL_ORIENTATIONS_LABEL.casefold():
        return tuple(OrientationCode)
    codes: list[OrientationCode] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        found = parse_enum_label(
            ORIENTATION_LABELS, part, field_name="Orientaciones", row_number=row_number
        )
        codes.append(found)
    return tuple(codes) if codes else tuple(OrientationCode)


def _format_orientations(codes: tuple[OrientationCode, ...]) -> str:
    if set(codes) == set(OrientationCode):
        return _ALL_ORIENTATIONS_LABEL
    return ", ".join(ORIENTATION_LABELS[code] for code in codes)


def load_unit_to_row(unit: LoadUnit) -> tuple[Any, ...]:
    """Traduce un `LoadUnit` a una fila de celdas, en el mismo orden que `PRODUCT_COLUMNS`."""
    return (
        unit.sku,
        unit.name,
        unit.dimensions.length_cm,
        unit.dimensions.width_cm,
        unit.dimensions.height_cm,
        unit.weight_kg,
        unit.quantity,
        unit.color_hex,
        format_bool(unit.fragile),
        _label_for(PACKAGE_TYPE_LABELS, unit.package_type),
        format_bool(unit.is_extinguisher),
        (
            ""
            if unit.extinguisher_agent is ExtinguisherAgent.NOT_APPLICABLE
            else _label_for(EXTINGUISHER_AGENT_LABELS, unit.extinguisher_agent)
        ),
        unit.extinguisher_nominal_kg,
        unit.max_stack_count,
        _format_orientations(unit.allowed_orientation_codes),
        unit.notes,
    )


def row_to_load_unit(
    row_number: int,
    values: tuple[object, ...],
    *,
    existing_colors: Sequence[str] = (),
) -> LoadUnit:
    """Reconstruye un `LoadUnit` a partir de una fila; valida completamente con el dominio.

    Lanza `RowConversionError` (capturada por el importador, nunca
    propagada tal cual) tanto para errores de formato (números
    inválidos, booleanos irreconocibles) como para violaciones de
    invariantes de dominio (`DomainValidationError`, p. ej. un extintor
    sin agente): ambas terminan siendo, desde el punto de vista del
    usuario, "esta fila no se pudo importar, y esto es exactamente lo
    que falla".

    `existing_colors` (fase OPT-18): igual que en
    `CatalogProductEditorDialog` (fase OPT-17), una celda "Color" vacía
    ya no se traduce silenciosamente en el gris `#CCCCCC` por defecto de
    `LoadUnit` — se asigna un color pastel automático
    (`domain.color_suggestions.suggest_pastel_color`), distinto de
    `existing_colors` mientras haya matices libres. Un color hexadecimal
    explícito en la celda (`#RRGGBB`, validado por `LoadUnit` en su
    `__post_init__`) siempre se respeta tal cual, nunca se sobrescribe.
    """
    (
        sku_raw,
        name_raw,
        length_raw,
        width_raw,
        height_raw,
        weight_raw,
        quantity_raw,
        color_raw,
        fragile_raw,
        package_type_raw,
        extinguisher_raw,
        agent_raw,
        nominal_raw,
        stack_raw,
        orientations_raw,
        notes_raw,
    ) = values

    sku = "" if sku_raw is None else str(sku_raw).strip()
    if not sku:
        raise RowConversionError(row_number, "'SKU' no puede estar vacío.")
    name = "" if name_raw is None else str(name_raw).strip()
    if not name:
        raise RowConversionError(row_number, "'Nombre' no puede estar vacío.")

    length_cm = parse_required_float(length_raw, field_name="Largo (cm)", row_number=row_number)
    width_cm = parse_required_float(width_raw, field_name="Ancho (cm)", row_number=row_number)
    height_cm = parse_required_float(height_raw, field_name="Alto (cm)", row_number=row_number)
    weight_kg = parse_required_float(weight_raw, field_name="Peso (kg)", row_number=row_number)
    quantity = parse_int(quantity_raw, field_name="Cantidad", row_number=row_number, default=1)
    color_hex = "" if color_raw is None else str(color_raw).strip()
    fragile = parse_bool(fragile_raw, field_name="Fragil", row_number=row_number, default=False)
    package_type = (
        PackageType.INDIVIDUAL
        if is_blank(package_type_raw)
        else parse_enum_label(
            PACKAGE_TYPE_LABELS,
            package_type_raw,
            field_name="Tipo de empaque",
            row_number=row_number,
        )
    )
    is_extinguisher = parse_bool(
        extinguisher_raw, field_name="Extintor", row_number=row_number, default=False
    )
    extinguisher_agent: object = ExtinguisherAgent.NOT_APPLICABLE
    if is_extinguisher:
        extinguisher_agent = parse_enum_label(
            EXTINGUISHER_AGENT_LABELS, agent_raw, field_name="Agente", row_number=row_number
        )
    extinguisher_nominal_kg = parse_optional_float(
        nominal_raw, field_name="Peso nominal (kg)", row_number=row_number
    )
    max_stack_count = parse_int(
        stack_raw, field_name="Apilamiento", row_number=row_number, default=DEFAULT_MAX_STACK_COUNT
    )
    allowed_orientations = _parse_orientations(orientations_raw, row_number=row_number)
    notes = "" if notes_raw is None else str(notes_raw).strip()

    kwargs: dict[str, object] = dict(
        sku=sku,
        name=name,
        dimensions=Dimensions3D(length_cm, width_cm, height_cm),
        weight_kg=weight_kg,
        quantity=quantity,
        package_type=package_type,
        max_stack_count=max_stack_count,
        allowed_orientation_codes=allowed_orientations,
        fragile=fragile,
        is_extinguisher=is_extinguisher,
        extinguisher_agent=extinguisher_agent,
        extinguisher_nominal_kg=extinguisher_nominal_kg,
        notes=notes,
        id=uuid4(),
    )
    kwargs["color_hex"] = color_hex if color_hex else suggest_pastel_color(existing_colors)

    try:
        return LoadUnit(**kwargs)  # type: ignore[arg-type]
    except DomainValidationError as exc:
        raise RowConversionError(row_number, str(exc)) from exc


def duplicate_unit_with_new_id(unit: LoadUnit) -> LoadUnit:
    """Copia independiente con UUID nuevo (mismo criterio que `CatalogService.copy_to_project`)."""
    return replace(unit, id=uuid4())
