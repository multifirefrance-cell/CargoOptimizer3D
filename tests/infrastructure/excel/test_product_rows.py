"""Pruebas de `infrastructure/excel/product_rows.py`: conversión fila <-> LoadUnit."""

from __future__ import annotations

import pytest

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.product_rows import (
    PRODUCT_COLUMNS,
    RowConversionError,
    load_unit_to_row,
    row_to_load_unit,
)


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


def test_round_trip_with_all_orientations() -> None:
    unit = LoadUnit(
        sku="SKU-2",
        name="Pallet",
        dimensions=Dimensions3D(120, 100, 110),
        weight_kg=300.0,
        package_type=PackageType.PALLET,
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
