"""Pruebas de `SelectionDetailsPanel`."""

from __future__ import annotations

from uuid import uuid4

from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.panels.selection_details_panel import (
    SelectionDetailsPanel,
)
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel

_EMPTY = "—"


def _visual(**overrides: object) -> PlacementVisualModel:
    kwargs: dict[str, object] = {
        "sequence_number": 3,
        "instance_number": 2,
        "load_unit_id": uuid4(),
        "sku": "BOX-9",
        "name": "Caja nueve",
        "position": (10.0, 20.0, 30.0),
        "oriented_dimensions": (40.0, 30.0, 20.0),
        "orientation_code": "lwh_xyz",
        "weight_kg": 12.5,
        "package_type": "individual",
        "units_per_package": 1,
        "is_extinguisher": False,
        "extinguisher_nominal_kg": None,
        "fragile": True,
        "max_stack_count": 2,
        "notes": "Frágil, manejar con cuidado.",
        "color_hex": "#4C78A8",
    }
    kwargs.update(overrides)
    return PlacementVisualModel(**kwargs)  # type: ignore[arg-type]


def test_panel_starts_empty(qapp: QApplication) -> None:
    panel = SelectionDetailsPanel()
    assert panel._sku_label.text() == _EMPTY
    assert panel._notes_text.toPlainText() == ""


def test_display_placement_populates_all_fields(qapp: QApplication) -> None:
    panel = SelectionDetailsPanel()
    panel.display_placement(_visual())

    assert panel._sku_label.text() == "BOX-9"
    assert panel._name_label.text() == "Caja nueve"
    assert panel._instance_label.text() == "2"
    assert panel._sequence_label.text() == "3"
    assert panel._position_label.text() == "10.0 / 20.0 / 30.0"
    assert panel._dimensions_label.text() == "40.0 / 30.0 / 20.0"
    assert panel._orientation_label.text() == "lwh_xyz"
    assert panel._weight_label.text() == "12.5 kg"
    assert panel._package_type_label.text() == "individual"
    assert panel._units_per_package_label.text() == "1"
    assert panel._extinguisher_label.text() == "No"
    assert panel._extinguisher_nominal_label.text() == _EMPTY
    assert panel._fragile_label.text() == "Sí"
    assert panel._max_stack_label.text() == "2"
    assert panel._notes_text.toPlainText() == "Frágil, manejar con cuidado."


def test_display_placement_shows_extinguisher_nominal_when_present(qapp: QApplication) -> None:
    panel = SelectionDetailsPanel()
    panel.display_placement(_visual(is_extinguisher=True, extinguisher_nominal_kg=5.0))
    assert panel._extinguisher_label.text() == "Sí"
    assert panel._extinguisher_nominal_label.text() == "5.0 kg"


def test_clear_resets_all_fields(qapp: QApplication) -> None:
    panel = SelectionDetailsPanel()
    panel.display_placement(_visual())
    panel.clear()

    assert panel._sku_label.text() == _EMPTY
    assert panel._name_label.text() == _EMPTY
    assert panel._instance_label.text() == _EMPTY
    assert panel._sequence_label.text() == _EMPTY
    assert panel._position_label.text() == _EMPTY
    assert panel._notes_text.toPlainText() == ""


def test_display_placement_distinguishes_instance_and_sequence_numbers(
    qapp: QApplication,
) -> None:
    panel = SelectionDetailsPanel()
    panel.display_placement(_visual(sequence_number=7, instance_number=1))
    assert panel._sequence_label.text() == "7"
    assert panel._instance_label.text() == "1"
    assert panel._sequence_label.text() != panel._instance_label.text()
