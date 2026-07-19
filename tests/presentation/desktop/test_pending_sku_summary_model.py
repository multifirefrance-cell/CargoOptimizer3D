"""Pruebas de `PendingSkuSummaryModel`: desglose de unidades pendientes por SKU (Parte 8)."""

from __future__ import annotations

from uuid import uuid4

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.models.pending_sku_summary_model import (
    COL_NAME,
    COL_PACKED,
    COL_PENDING,
    COL_REQUESTED,
    COL_SKU,
    PendingSkuSummaryModel,
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


_ORIENTATION = Orientation.from_base_dimensions(
    Dimensions3D(40.0, 30.0, 20.0), OrientationCode.LWH_XYZ
)


def _placement(load_unit_id: object, instance_number: int, sequence_number: int) -> Placement:
    return Placement(
        load_unit_id=load_unit_id,  # type: ignore[arg-type]
        instance_number=instance_number,
        position=Position3D(0.0, 0.0, 0.0),
        orientation=_ORIENTATION,
        sequence_number=sequence_number,
    )


def _unpacked(load_unit_id: object, instance_number: int) -> UnpackedUnit:
    return UnpackedUnit(
        load_unit_id=load_unit_id,  # type: ignore[arg-type]
        instance_number=instance_number,
        reason_code="no_feasible_position",
        reason_message="No cupo en ningún lado.",
    )


def test_empty_result_has_no_rows(qapp: QApplication) -> None:
    model = PendingSkuSummaryModel()
    model.set_result((), (), {})
    assert model.rowCount() == 0


def test_fully_loaded_sku_does_not_appear(qapp: QApplication) -> None:
    unit = _unit(sku="FULL-1")
    placements = tuple(_placement(unit.id, i, i) for i in range(1, 6))
    model = PendingSkuSummaryModel()

    model.set_result(placements, (), {unit.id: unit})

    assert model.rowCount() == 0


def test_partially_loaded_sku_shows_exact_counts(qapp: QApplication) -> None:
    unit = _unit(sku="PARTIAL-1", name="Producto parcial")
    placements = tuple(_placement(unit.id, i, i) for i in range(1, 86))  # 85 cargados
    unpacked = tuple(_unpacked(unit.id, i) for i in range(86, 101))  # 15 pendientes
    model = PendingSkuSummaryModel()

    model.set_result(placements, unpacked, {unit.id: unit})

    assert model.rowCount() == 1
    assert model.data(model.index(0, COL_SKU)) == "PARTIAL-1"
    assert model.data(model.index(0, COL_NAME)) == "Producto parcial"
    assert model.data(model.index(0, COL_REQUESTED)) == 100
    assert model.data(model.index(0, COL_PACKED)) == 85
    assert model.data(model.index(0, COL_PENDING)) == 15


def test_sku_with_zero_packed_units_appears_correctly(qapp: QApplication) -> None:
    unit = _unit(sku="ZERO-PACKED")
    unpacked = tuple(_unpacked(unit.id, i) for i in range(1, 11))  # 10 pendientes, 0 cargados
    model = PendingSkuSummaryModel()

    model.set_result((), unpacked, {unit.id: unit})

    assert model.rowCount() == 1
    assert model.data(model.index(0, COL_PACKED)) == 0
    assert model.data(model.index(0, COL_PENDING)) == 10
    assert model.data(model.index(0, COL_REQUESTED)) == 10


def test_multiple_skus_sorted_by_sku(qapp: QApplication) -> None:
    unit_a = _unit(sku="ZZZ-LAST")
    unit_b = _unit(sku="AAA-FIRST")
    placements = tuple(_placement(unit_a.id, i, i) for i in range(1, 6)) + tuple(
        _placement(unit_b.id, i, 100 + i) for i in range(1, 3)
    )
    unpacked = tuple(_unpacked(unit_a.id, i) for i in range(6, 9)) + tuple(
        _unpacked(unit_b.id, i) for i in range(3, 5)
    )
    model = PendingSkuSummaryModel()

    model.set_result(placements, unpacked, {unit_a.id: unit_a, unit_b.id: unit_b})

    assert model.rowCount() == 2
    assert model.data(model.index(0, COL_SKU)) == "AAA-FIRST"
    assert model.data(model.index(1, COL_SKU)) == "ZZZ-LAST"


def test_sum_of_individual_pending_matches_total_pending_count(qapp: QApplication) -> None:
    unit_a = _unit(sku="SUM-A")
    unit_b = _unit(sku="SUM-B")
    unit_c = _unit(sku="SUM-C")
    placements = tuple(_placement(unit_a.id, i, i) for i in range(1, 11))
    unpacked = (
        tuple(_unpacked(unit_a.id, i) for i in range(11, 16))  # 5
        + tuple(_unpacked(unit_b.id, i) for i in range(1, 4))  # 3
        + tuple(_unpacked(unit_c.id, i) for i in range(1, 2))  # 1
    )
    model = PendingSkuSummaryModel()

    model.set_result(
        placements, unpacked, {unit_a.id: unit_a, unit_b.id: unit_b, unit_c.id: unit_c}
    )

    total_pending_from_rows = sum(
        model.data(model.index(row, COL_PENDING)) for row in range(model.rowCount())
    )
    assert total_pending_from_rows == len(unpacked)


def test_unknown_load_unit_falls_back_to_uuid_and_dash_name(qapp: QApplication) -> None:
    unknown_id = uuid4()
    unpacked = (_unpacked(unknown_id, 1),)
    model = PendingSkuSummaryModel()

    model.set_result((), unpacked, {})

    assert model.data(model.index(0, COL_SKU)) == str(unknown_id)
    assert model.data(model.index(0, COL_NAME)) == "—"


def test_clear_resets_model(qapp: QApplication) -> None:
    unit = _unit(sku="TO-CLEAR")
    model = PendingSkuSummaryModel()
    model.set_result((), (_unpacked(unit.id, 1),), {unit.id: unit})
    assert model.rowCount() == 1

    model.clear()

    assert model.rowCount() == 0
