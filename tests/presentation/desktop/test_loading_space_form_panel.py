"""Pruebas de `LoadingSpaceFormPanel`: carga de perfiles y modo personalizado."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    PROFILE_CUSTOM,
    LoadingSpaceFormPanel,
)


def test_default_profile_is_20ft_container(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    assert panel.current_profile_name() == "Contenedor 20'"
    space = panel.build_loading_space()
    assert space is not None
    assert space.internal_dimensions.length_cm == 589.0


def test_fields_are_locked_for_a_predefined_profile(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    assert not panel._name_edit.isEnabled()
    assert not panel._length_spin.isEnabled()


def test_selecting_custom_unlocks_all_fields(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    panel.set_current_profile_name(PROFILE_CUSTOM)
    assert panel._name_edit.isEnabled()
    assert panel._length_spin.isEnabled()
    assert panel._category_combo.isEnabled()
    assert panel._notes_edit.isEnabled()


def test_switching_profile_loads_expected_dimensions(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    panel.set_current_profile_name("Bodega")
    space = panel.build_loading_space()
    assert space is not None
    assert space.max_weight_kg is None
    assert space.internal_dimensions.length_cm == 2000.0


def test_set_current_profile_name_ignores_unknown_profile(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    panel.set_current_profile_name("Perfil inexistente")
    assert panel.current_profile_name() == "Contenedor 20'"


def test_build_loading_space_returns_valid_space_for_every_profile(qapp: QApplication) -> None:
    panel = LoadingSpaceFormPanel()
    for index in range(panel._profile_combo.count()):
        profile_name = panel._profile_combo.itemText(index)
        panel.set_current_profile_name(profile_name)
        space = panel.build_loading_space()
        assert space is not None, f"Perfil '{profile_name}' no produjo un LoadingSpace válido"
