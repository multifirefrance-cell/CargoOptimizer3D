"""Pruebas de `UnpackedUnitTableModel`."""

from __future__ import annotations

from uuid import uuid4

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.models.unpacked_table_model import (
    COL_CODE,
    COL_INSTANCE,
    COL_REASON,
    COL_SKU,
    UnpackedUnitTableModel,
)


def _unit(**overrides: object) -> LoadUnit:
    kwargs: dict[str, object] = {
        "sku": "BOX-1",
        "name": "Caja",
        "dimensions": Dimensions3D(40.0, 30.0, 20.0),
        "weight_kg": 10.0,
    }
    kwargs.update(overrides)
    return LoadUnit(**kwargs)  # type: ignore[arg-type]


def test_empty_model_has_no_rows(qapp: QApplication) -> None:
    model = UnpackedUnitTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 4


def test_data_maps_load_unit_id_to_sku(qapp: QApplication) -> None:
    unit = _unit(sku="MISSING-BOX")
    unpacked = UnpackedUnit(
        load_unit_id=unit.id,
        instance_number=2,
        reason_code="no_feasible_position",
        reason_message="No cupo en ningún lado.",
    )
    model = UnpackedUnitTableModel()
    model.set_unpacked_units((unpacked,), {unit.id: unit})

    assert model.rowCount() == 1
    assert model.data(model.index(0, COL_SKU)) == "MISSING-BOX"
    assert model.data(model.index(0, COL_INSTANCE)) == 2
    assert model.data(model.index(0, COL_REASON)) == "No cupo en ningún lado."
    assert model.data(model.index(0, COL_CODE)) == "no_feasible_position"


def test_data_falls_back_to_uuid_when_load_unit_missing(qapp: QApplication) -> None:
    unknown_id = uuid4()
    unpacked = UnpackedUnit(
        load_unit_id=unknown_id, instance_number=1, reason_code="x", reason_message="y"
    )
    model = UnpackedUnitTableModel()
    model.set_unpacked_units((unpacked,), {})

    assert model.data(model.index(0, COL_SKU)) == str(unknown_id)


def test_clear_resets_model(qapp: QApplication) -> None:
    unit = _unit()
    unpacked = UnpackedUnit(
        load_unit_id=unit.id, instance_number=1, reason_code="x", reason_message="y"
    )
    model = UnpackedUnitTableModel()
    model.set_unpacked_units((unpacked,), {unit.id: unit})
    model.clear()
    assert model.rowCount() == 0
