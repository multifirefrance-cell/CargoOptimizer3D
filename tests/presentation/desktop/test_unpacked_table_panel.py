"""Pruebas de `UnpackedTablePanel`: wiring del resumen por SKU + detalle por instancia."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.orientation import Orientation
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.position import Position3D
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.panels.unpacked_table_panel import UnpackedTablePanel

_ORIENTATION = Orientation.from_base_dimensions(
    Dimensions3D(40.0, 30.0, 20.0), OrientationCode.LWH_XYZ
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


def test_set_result_updates_both_summary_and_detail_models(qapp: QApplication) -> None:
    unit = _unit(sku="PANEL-1")
    placements = (_placement(unit.id, 1, 1), _placement(unit.id, 2, 2))
    unpacked = (_unpacked(unit.id, 3),)
    panel = UnpackedTablePanel()

    panel.set_result(placements, unpacked, {unit.id: unit})

    assert panel.pending_summary_model.rowCount() == 1
    assert panel.model.rowCount() == 1


def test_fully_loaded_sku_does_not_appear_in_summary_but_has_no_detail_rows(
    qapp: QApplication,
) -> None:
    unit = _unit(sku="PANEL-FULL")
    placements = (_placement(unit.id, 1, 1),)
    panel = UnpackedTablePanel()

    panel.set_result(placements, (), {unit.id: unit})

    assert panel.pending_summary_model.rowCount() == 0
    assert panel.model.rowCount() == 0


def test_clear_resets_both_models(qapp: QApplication) -> None:
    unit = _unit(sku="PANEL-CLEAR")
    panel = UnpackedTablePanel()
    panel.set_result((), (_unpacked(unit.id, 1),), {unit.id: unit})
    assert panel.pending_summary_model.rowCount() == 1
    assert panel.model.rowCount() == 1

    panel.clear()

    assert panel.pending_summary_model.rowCount() == 0
    assert panel.model.rowCount() == 0


def test_summary_table_view_has_bounded_height_and_both_views_stretch(
    qapp: QApplication,
) -> None:
    # El resumen tiene una altura acotada (no crece sin límite si hay
    # muchos SKU pendientes), pero -- a diferencia del diseño anterior,
    # donde solo el detalle tenía stretch y el resumen quedaba fijo en su
    # sizeHint (~30px reales, verificado con un PackingResult real) --
    # ahora ambos widgets reciben stretch, con el resumen como prioridad
    # (2:1) por ser la información más relevante de la pestaña.
    panel = UnpackedTablePanel()
    layout = panel.layout()
    assert layout is not None
    assert panel.summary_table_view.maximumHeight() <= 250
    summary_index = layout.indexOf(panel.summary_table_view)
    detail_index = layout.indexOf(panel.table_view)
    assert layout.stretch(summary_index) > 0
    assert layout.stretch(detail_index) > 0
    assert layout.stretch(summary_index) >= layout.stretch(detail_index)
