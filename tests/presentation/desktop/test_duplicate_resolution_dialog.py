"""Pruebas de `DuplicateResolutionDialog`: por fila, "aplicar a todos" y cancelar (fase 8.1)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.dialogs.duplicate_resolution_dialog import (
    DuplicateResolutionDialog,
)


def _unit(sku: str) -> LoadUnit:
    return LoadUnit(
        sku=sku, name=f"Producto {sku}", dimensions=Dimensions3D(50, 40, 30), weight_kg=10.0
    )


def test_default_action_for_each_row_is_update(qapp: QApplication) -> None:
    units = (_unit("A"), _unit("B"))
    dialog = DuplicateResolutionDialog(None, existing_units=units)

    dialog._on_accept()

    assert dialog.result_resolutions() == {"A": "update", "B": "update"}


def test_per_row_action_can_be_changed_independently(qapp: QApplication) -> None:
    units = (_unit("A"), _unit("B"))
    dialog = DuplicateResolutionDialog(None, existing_units=units)

    dialog._action_combos[0].setCurrentText("Duplicar")
    dialog._action_combos[1].setCurrentText("Ignorar")
    dialog._on_accept()

    assert dialog.result_resolutions() == {"A": "duplicate", "B": "ignore"}


def test_apply_to_all_sets_every_row_to_the_chosen_action(qapp: QApplication) -> None:
    units = (_unit("A"), _unit("B"), _unit("C"))
    dialog = DuplicateResolutionDialog(None, existing_units=units)
    dialog._action_combos[0].setCurrentText("Duplicar")

    dialog._apply_all_combo.setCurrentText("Ignorar")
    dialog._on_apply_all()
    dialog._on_accept()

    assert dialog.result_resolutions() == {"A": "ignore", "B": "ignore", "C": "ignore"}


def test_cancel_leaves_result_resolutions_as_none(qapp: QApplication) -> None:
    dialog = DuplicateResolutionDialog(None, existing_units=(_unit("A"),))

    dialog.reject()

    assert dialog.result_resolutions() is None
