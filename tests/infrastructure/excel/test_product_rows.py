"""Pruebas de `infrastructure/excel/product_rows.py`: conversión fila <-> LoadUnit."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.load_unit import (
    DEFAULT_MAX_STACK_COUNT,
    DEFAULT_ORIENTATION_CODES,
    LoadUnit,
)
from cargo_optimizer.infrastructure.excel.product_rows import (
    PRODUCT_COLUMNS,
    RowConversionError,
    load_unit_to_row,
    row_to_load_unit,
)

# Índice de la columna "Apilamiento" en la tupla de valores de fila (0-based),
# igual orden que PRODUCT_COLUMNS: sku, name, largo, ancho, alto, peso,
# cantidad, color, fragil, tipo_empaque, extintor, agente, peso_nominal,
# apilamiento, orientaciones, notas.
_STACK_COLUMN_INDEX = 13


def _row_with_stack_cell(stack_value: object) -> tuple[object, ...]:
    values: list[object] = [
        "SKU",
        "Nombre",
        10,
        10,
        10,
        1.0,
        1,
        "",
        "No",
        "",
        "No",
        "",
        "",
        stack_value,
        "",
        "",
    ]
    return tuple(values)


def test_round_trip_of_a_simple_product() -> None:
    unit = LoadUnit(
        sku="SKU-1",
        name="Caja de prueba",
        dimensions=Dimensions3D(50, 40, 30),
        weight_kg=12.5,
        quantity=3,
        notes="Notas de ejemplo",
    )
    row = load_unit_to_row(unit)
    assert len(row) == len(PRODUCT_COLUMNS)

    rebuilt = row_to_load_unit(2, row)
    assert rebuilt.sku == unit.sku
    assert rebuilt.name == unit.name
    assert rebuilt.dimensions == unit.dimensions
    assert rebuilt.weight_kg == unit.weight_kg
    assert rebuilt.quantity == unit.quantity
    assert rebuilt.notes == unit.notes
    assert rebuilt.color_hex == unit.color_hex


def test_round_trip_of_an_extinguisher() -> None:
    unit = LoadUnit(
        sku="EXT-1",
        name="Extintor CO2",
        dimensions=Dimensions3D(20, 20, 60),
        weight_kg=8.0,
        is_extinguisher=True,
        extinguisher_agent=ExtinguisherAgent.CO2,
        extinguisher_nominal_kg=5.0,
        allowed_orientation_codes=(OrientationCode.LWH_XYZ,),
        max_stack_count=1,
    )
    row = load_unit_to_row(unit)
    rebuilt = row_to_load_unit(2, row)

    assert rebuilt.is_extinguisher is True
    assert rebuilt.extinguisher_agent == ExtinguisherAgent.CO2
    assert rebuilt.extinguisher_nominal_kg == 5.0
    assert rebuilt.allowed_orientation_codes == (OrientationCode.LWH_XYZ,)


def test_blank_orientations_cell_means_reduced_default_not_all_six() -> None:
    """Fase OPT-17: una celda vacía en una importación nueva ya no significa "las 6"."""
    unit = LoadUnit(
        sku="SKU-3",
        name="Caja",
        dimensions=Dimensions3D(40, 30, 20),
        weight_kg=5.0,
    )
    row = load_unit_to_row(unit)
    assert unit.allowed_orientation_codes == DEFAULT_ORIENTATION_CODES
    rebuilt = row_to_load_unit(2, row)
    assert rebuilt.allowed_orientation_codes == DEFAULT_ORIENTATION_CODES


def test_explicit_todas_label_from_excel_still_means_all_six() -> None:
    """La etiqueta explícita "Todas" (de una exportación anterior a esta fase, o
    escrita a mano) sigue significando las 6 tal cual — no es un valor por defecto
    silencioso, es una elección explícita del usuario."""
    values = ("SKU-4", "Caja", 40, 30, 20, 5.0, 1, "", "No", "", "No", "", "", "", "Todas", "")
    unit = row_to_load_unit(2, values)
    assert set(unit.allowed_orientation_codes) == set(OrientationCode)


def test_round_trip_with_all_orientations() -> None:
    unit = LoadUnit(
        sku="SKU-2",
        name="Pallet",
        dimensions=Dimensions3D(120, 100, 110),
        weight_kg=300.0,
        package_type=PackageType.PALLET,
        allowed_orientation_codes=tuple(OrientationCode),
    )
    row = load_unit_to_row(unit)
    rebuilt = row_to_load_unit(2, row)
    assert set(rebuilt.allowed_orientation_codes) == set(OrientationCode)
    assert rebuilt.package_type == PackageType.PALLET


def test_row_to_load_unit_rejects_blank_sku() -> None:
    values = ("", "Nombre", 10, 10, 10, 1.0, 1, "", "", "", "", "", "", "", "", "")
    with pytest.raises(RowConversionError):
        row_to_load_unit(2, values)


def test_row_to_load_unit_rejects_non_numeric_dimension() -> None:
    values = ("SKU", "Nombre", "no-numerico", 10, 10, 1.0, 1, "", "", "", "", "", "", "", "", "")
    with pytest.raises(RowConversionError):
        row_to_load_unit(2, values)


def test_row_to_load_unit_rejects_invalid_package_type_label() -> None:
    values = (
        "SKU",
        "Nombre",
        10,
        10,
        10,
        1.0,
        1,
        "",
        "No",
        "Tipo inexistente",
        "No",
        "",
        "",
        1,
        "",
        "",
    )
    with pytest.raises(RowConversionError):
        row_to_load_unit(2, values)


def test_row_to_load_unit_rejects_extinguisher_without_agent() -> None:
    values = (
        "SKU",
        "Nombre",
        10,
        10,
        10,
        1.0,
        1,
        "",
        "No",
        "",
        "Si",
        "",
        "",
        1,
        "",
        "",
    )
    with pytest.raises(RowConversionError):
        row_to_load_unit(2, values)


def test_row_to_load_unit_reports_the_given_row_number() -> None:
    values = ("", "Nombre", 10, 10, 10, 1.0, 1, "", "", "", "", "", "", "", "", "")
    with pytest.raises(RowConversionError) as excinfo:
        row_to_load_unit(7, values)
    assert excinfo.value.row_number == 7


# --- Apilamiento máximo (fase OPT-14): entero normal, 1 = No apilable, --------
# --- N = límite exacto, celda vacía en una importación = DEFAULT_MAX_STACK_COUNT. -


def test_blank_max_stack_count_cell_means_default_not_one() -> None:
    """Una celda vacía nunca debe convertirse silenciosamente en "No apilable"."""
    unit = row_to_load_unit(2, _row_with_stack_cell(""))
    assert unit.max_stack_count == DEFAULT_MAX_STACK_COUNT
    assert unit.max_stack_count != 1


def test_missing_max_stack_count_cell_means_default_not_one() -> None:
    unit = row_to_load_unit(2, _row_with_stack_cell(None))
    assert unit.max_stack_count == DEFAULT_MAX_STACK_COUNT


def test_explicit_one_from_excel_means_not_stackable() -> None:
    unit = row_to_load_unit(2, _row_with_stack_cell(1))
    assert unit.max_stack_count == 1


def test_explicit_specific_limit_from_excel_is_preserved() -> None:
    unit = row_to_load_unit(2, _row_with_stack_cell(5))
    assert unit.max_stack_count == 5


def test_export_of_specific_limit_writes_the_number() -> None:
    unit = LoadUnit(
        sku="SKU-4",
        name="Producto con límite 3",
        dimensions=Dimensions3D(40, 30, 20),
        weight_kg=5.0,
        max_stack_count=3,
    )
    row = load_unit_to_row(unit)
    assert row[_STACK_COLUMN_INDEX] == 3


def test_round_trip_of_default_stack_count_value() -> None:
    """El valor por defecto (30) exporta e reimporta como un número normal, no como texto."""
    unit = LoadUnit(
        sku="SKU-5",
        name="Producto con límite por defecto",
        dimensions=Dimensions3D(40, 30, 20),
        weight_kg=5.0,
        max_stack_count=DEFAULT_MAX_STACK_COUNT,
    )
    row = load_unit_to_row(unit)
    assert row[_STACK_COLUMN_INDEX] == DEFAULT_MAX_STACK_COUNT
    rebuilt = row_to_load_unit(2, row)
    assert rebuilt.max_stack_count == DEFAULT_MAX_STACK_COUNT


def test_round_trip_of_not_stackable() -> None:
    unit = LoadUnit(
        sku="SKU-6",
        name="Producto no apilable",
        dimensions=Dimensions3D(40, 30, 20),
        weight_kg=5.0,
        max_stack_count=1,
    )
    row = load_unit_to_row(unit)
    rebuilt = row_to_load_unit(2, row)
    assert rebuilt.max_stack_count == 1
