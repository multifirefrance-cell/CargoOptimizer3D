"""Pruebas de `CatalogProductEditorDialog`, sin llamar a `exec()` (ver conftest.py)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, PackageType
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.dialogs.catalog_product_editor_dialog import (
    CatalogProductEditorDialog,
)


def test_new_dialog_has_sensible_defaults(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    assert dialog._color_edit.text() == "#CCCCCC"
    assert all(check.isChecked() for check in dialog._orientation_checks.values())


def test_editing_populates_fields_from_load_unit(qapp: QApplication) -> None:
    unit = LoadUnit(
        sku="BOX-1",
        name="Caja",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=12.5,
        fragile=True,
        notes="Notas",
    )
    dialog = CatalogProductEditorDialog(None, load_unit=unit)
    assert dialog._sku_edit.text() == "BOX-1"
    assert dialog._name_edit.text() == "Caja"
    assert dialog._weight_spin.value() == 12.5
    assert dialog._fragile_check.isChecked() is True
    assert dialog._notes_edit.toPlainText() == "Notas"


def test_build_load_unit_from_form_fields(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-9")
    dialog._name_edit.setText("Caja nueve")
    dialog._length_spin.setValue(50.0)
    dialog._width_spin.setValue(40.0)
    dialog._height_spin.setValue(30.0)
    dialog._weight_spin.setValue(15.0)

    unit = dialog._build_load_unit()

    assert unit.sku == "BOX-9"
    assert unit.name == "Caja nueve"
    assert unit.dimensions.as_tuple() == (50.0, 40.0, 30.0)
    assert unit.weight_kg == 15.0


def test_accepting_with_valid_data_sets_result_and_accepts(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-1")
    dialog._name_edit.setText("Caja")

    dialog._on_accept()

    assert dialog.result_load_unit() is not None
    assert dialog.result_load_unit().sku == "BOX-1"  # type: ignore[union-attr]


def test_accepting_with_empty_sku_shows_warning_and_does_not_accept(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    warnings: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *args, **_kwargs: warnings.append(args)),
    )
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("")
    dialog._name_edit.setText("Caja")

    dialog._on_accept()

    assert dialog.result_load_unit() is None
    assert len(warnings) == 1


def test_editing_extinguisher_toggles_enable_agent_and_nominal_fields(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    assert dialog._extinguisher_agent_combo.isEnabled() is False
    dialog._is_extinguisher_check.setChecked(True)
    assert dialog._extinguisher_agent_combo.isEnabled() is True
    assert dialog._extinguisher_nominal_spin.isEnabled() is True


def test_build_load_unit_with_extinguisher_fields(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("EXT-1")
    dialog._name_edit.setText("Extintor")
    dialog._is_extinguisher_check.setChecked(True)
    index = dialog._extinguisher_agent_combo.findData(ExtinguisherAgent.CO2)
    dialog._extinguisher_agent_combo.setCurrentIndex(index)
    dialog._extinguisher_nominal_spin.setValue(5.0)

    unit = dialog._build_load_unit()

    assert unit.is_extinguisher is True
    assert unit.extinguisher_agent == ExtinguisherAgent.CO2
    assert unit.extinguisher_nominal_kg == 5.0


def test_package_type_individual_forces_units_per_package_one(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-1")
    dialog._name_edit.setText("Caja")
    index = dialog._package_type_combo.findData(PackageType.INDIVIDUAL)
    dialog._package_type_combo.setCurrentIndex(index)
    dialog._units_per_package_spin.setValue(6)

    unit = dialog._build_load_unit()

    assert unit.units_per_package == 1
