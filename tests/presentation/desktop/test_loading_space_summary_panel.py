"""Pruebas de `LoadingSpaceSummaryPanel`: Tipo/Perfil compactos + resumen + "Cambiar medidas…".

No duplica ningún `LoadingSpace` real: solo agrupa los perfiles ya
definidos por `loading_space_form_panel.loading_space_profiles()` por
categoría y expone un resumen de solo lectura sincronizado desde el
`LoadingSpaceFormPanel` real (probado en combinación en
`test_main_window.py`).
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import PROFILE_CUSTOM
from cargo_optimizer.presentation.desktop.panels.loading_space_summary_panel import (
    LoadingSpaceSummaryPanel,
)


def test_type_combo_groups_profiles_by_category(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    type_labels = [panel._type_combo.itemText(i) for i in range(panel._type_combo.count())]
    assert "Contenedor" in type_labels
    assert type_labels[-1] == PROFILE_CUSTOM


def test_selecting_type_populates_matching_profiles(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    panel._type_combo.setCurrentText("Contenedor")
    profile_names = [panel._profile_combo.itemText(i) for i in range(panel._profile_combo.count())]
    assert "Contenedor 20'" in profile_names


def test_selecting_custom_type_disables_profile_combo(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    panel._type_combo.setCurrentText(PROFILE_CUSTOM)
    assert not panel._profile_combo.isEnabled()
    assert panel._profile_combo.currentText() == PROFILE_CUSTOM


def test_changing_profile_emits_profile_selected(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    received: list[str] = []
    panel.profile_selected.connect(received.append)

    panel._type_combo.setCurrentText("Contenedor")
    panel._profile_combo.setCurrentText("Contenedor 40'")

    assert "Contenedor 40'" in received


def test_set_current_profile_does_not_reemit_profile_selected(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    received: list[str] = []
    panel.profile_selected.connect(received.append)

    panel.set_current_profile("Contenedor 40'")

    assert received == []
    assert panel._type_combo.currentText() == "Contenedor"
    assert panel._profile_combo.currentText() == "Contenedor 40'"


def test_set_current_profile_custom_selects_custom_type(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    panel.set_current_profile(PROFILE_CUSTOM)
    assert panel._type_combo.currentText() == PROFILE_CUSTOM


def test_change_button_emits_change_requested(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    received = []
    panel.change_requested.connect(lambda: received.append(1))

    panel._change_button.click()

    assert received == [1]


def test_set_summary_none_shows_empty_placeholders(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    panel.set_summary(None)
    assert panel._dimensions_label.text() == "—"
    assert panel._weight_label.text() == "—"


def test_set_summary_with_space_shows_dimensions_and_weight(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    space = LoadingSpace(
        name="Contenedor 20'",
        category=LoadingSpaceCategory.CONTAINER,
        internal_dimensions=Dimensions3D(589.0, 235.0, 239.0),
        max_weight_kg=28180.0,
    )

    panel.set_summary(space)

    assert "589" in panel._dimensions_label.text()
    assert "235" in panel._dimensions_label.text()
    assert "239" in panel._dimensions_label.text()
    assert "28.180" in panel._weight_label.text() or "28180" in panel._weight_label.text()


def test_set_summary_with_unlimited_weight(qapp: QApplication) -> None:
    panel = LoadingSpaceSummaryPanel()
    space = LoadingSpace(
        name="Bodega",
        category=LoadingSpaceCategory.WAREHOUSE,
        internal_dimensions=Dimensions3D(1000.0, 800.0, 400.0),
        max_weight_kg=None,
    )

    panel.set_summary(space)

    assert panel._weight_label.text() == "Sin límite de peso"
