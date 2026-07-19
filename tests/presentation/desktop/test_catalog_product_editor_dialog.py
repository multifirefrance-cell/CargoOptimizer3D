"""Pruebas de `CatalogProductEditorDialog`, sin llamar a `exec()` (ver conftest.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QColorDialog, QMessageBox

from cargo_optimizer.domain.color_suggestions import _HEX_COLOR_PATTERN
from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.load_unit import DEFAULT_ORIENTATION_CODES, LoadUnit
from cargo_optimizer.infrastructure.database.engine import DatabaseManager
from cargo_optimizer.infrastructure.database.paths import get_user_database_path
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.dialogs.catalog_product_editor_dialog import (
    CatalogProductEditorDialog,
)


def test_new_dialog_has_sensible_defaults(qapp: QApplication) -> None:
    """Fase OPT-17: un producto nuevo recibe un color pastel automático (hex válido,
    no necesariamente "#CCCCCC") y solo las 2 orientaciones horizontales por defecto."""
    dialog = CatalogProductEditorDialog(None)
    assert _HEX_COLOR_PATTERN.match(dialog._color_edit.text())
    for code, check in dialog._orientation_checks.items():
        assert check.isChecked() == (code in DEFAULT_ORIENTATION_CODES)


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


def test_build_load_unit_package_type_is_a_real_enum_instance(qapp: QApplication) -> None:
    # Regresión: `QComboBox.currentData()` pasa por `QVariant`, y un
    # `StrEnum` (subclase de `str`) puede volver como un `str` plano en
    # vez del enum original — comparar por igualdad (`== PackageType.X`)
    # no lo detecta, porque un `str` con el mismo valor sigue comparando
    # igual. Solo `isinstance`/`type()` expone el problema, y solo se
    # nota de verdad al pasar el `LoadUnit` a
    # `ProductCatalogRepository.add()`, que lanza `AttributeError` al
    # leer `.value` de un `str` plano (bug real encontrado al crear un
    # producto nuevo desde `ProductQuickAddPanel`).
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-1")
    dialog._name_edit.setText("Caja")

    unit = dialog._build_load_unit()

    assert isinstance(unit.package_type, PackageType)
    assert type(unit.package_type) is PackageType


def test_build_load_unit_extinguisher_agent_is_a_real_enum_instance(qapp: QApplication) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("EXT-1")
    dialog._name_edit.setText("Extintor")
    dialog._is_extinguisher_check.setChecked(True)
    index = dialog._extinguisher_agent_combo.findData(ExtinguisherAgent.CO2)
    dialog._extinguisher_agent_combo.setCurrentIndex(index)

    unit = dialog._build_load_unit()

    assert isinstance(unit.extinguisher_agent, ExtinguisherAgent)
    assert type(unit.extinguisher_agent) is ExtinguisherAgent


def test_build_load_unit_can_be_added_to_a_real_sqlite_repository(
    qapp: QApplication, tmp_path: Path
) -> None:
    # Regresión de extremo a extremo: antes de la corrección,
    # `ProductCatalogRepository.add()` lanzaba `AttributeError: 'str'
    # object has no attribute 'value'` al intentar leer
    # `load_unit.package_type.value` sobre el `str` plano que devolvía
    # `QComboBox.currentData()` — el usuario podía rellenar "Crear nuevo
    # SKU…", pulsar Aceptar, y el producto nunca se guardaba en el
    # catálogo, sin ningún error visible (`_on_create_new_sku` solo
    # capturaba `RepositoryError`, no `AttributeError`).
    manager = DatabaseManager(get_user_database_path(base_dir=tmp_path))
    manager.initialize()
    repo = ProductCatalogRepository(manager)

    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("NEW-SKU-1")
    dialog._name_edit.setText("Producto nuevo")

    unit = dialog._build_load_unit()
    added = repo.add(unit)

    assert repo.get_by_sku("NEW-SKU-1") is not None
    assert added.sku == "NEW-SKU-1"


def test_manual_orientation_edit_is_honored(qapp: QApplication) -> None:
    """Fase OPT-17: el administrador puede habilitar más orientaciones a mano."""
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-1")
    dialog._name_edit.setText("Caja")
    for check in dialog._orientation_checks.values():
        check.setChecked(True)

    unit = dialog._build_load_unit()

    assert set(unit.allowed_orientation_codes) == set(OrientationCode)


def test_editing_existing_product_keeps_its_configured_orientations(qapp: QApplication) -> None:
    """Fase OPT-17: abrir un producto ya configurado nunca le cambia las orientaciones."""
    unit = LoadUnit(
        sku="BOX-2",
        name="Caja",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=5.0,
        allowed_orientation_codes=tuple(OrientationCode),
    )
    dialog = CatalogProductEditorDialog(None, load_unit=unit)
    for code, check in dialog._orientation_checks.items():
        assert check.isChecked() == (code in unit.allowed_orientation_codes)

    rebuilt = dialog._build_load_unit()
    assert set(rebuilt.allowed_orientation_codes) == set(OrientationCode)


def test_existing_colors_are_never_used_for_an_existing_products_color(
    qapp: QApplication,
) -> None:
    """Fase OPT-17: `existing_colors` solo influye en un SKU NUEVO, nunca sobrescribe uno
    guardado."""
    unit = LoadUnit(
        sku="BOX-3",
        name="Caja",
        dimensions=Dimensions3D(40.0, 30.0, 20.0),
        weight_kg=5.0,
        color_hex="#123456",
    )
    dialog = CatalogProductEditorDialog(
        None, load_unit=unit, existing_colors=("#AAAAAA", "#BBBBBB")
    )
    assert dialog._color_edit.text() == "#123456"


def test_new_product_pastel_color_avoids_existing_colors(qapp: QApplication) -> None:
    dialog_no_existing = CatalogProductEditorDialog(None)
    dialog_with_existing = CatalogProductEditorDialog(
        None, existing_colors=(dialog_no_existing._color_edit.text(),)
    )
    assert dialog_with_existing._color_edit.text() != dialog_no_existing._color_edit.text()


def test_color_picker_button_updates_color_edit(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fase OPT-17: selector visual de color — el botón "..." abre `QColorDialog`."""
    dialog = CatalogProductEditorDialog(None)
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *_a, **_k: QColor("#336699")))

    dialog._on_pick_color()

    assert dialog._color_edit.text() == "#336699"


def test_color_picker_cancelled_keeps_previous_color(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._color_edit.setText("#ABCDEF")
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *_a, **_k: QColor()))

    dialog._on_pick_color()

    assert dialog._color_edit.text() == "#ABCDEF"


def test_manually_picked_color_round_trips_through_build_load_unit(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog = CatalogProductEditorDialog(None)
    dialog._sku_edit.setText("BOX-4")
    dialog._name_edit.setText("Caja")
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *_a, **_k: QColor("#00FF7F")))
    dialog._on_pick_color()

    unit = dialog._build_load_unit()

    assert unit.color_hex == "#00FF7F"
