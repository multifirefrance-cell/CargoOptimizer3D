"""Pruebas de `ProjectTreePanel` (guía de 5 pasos, rediseño UX)."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.panels.project_tree_panel import (
    STEP_CURRENT,
    STEP_DONE,
    STEP_EXPORT,
    STEP_OPTIMIZE,
    STEP_PENDING,
    STEP_PRODUCTS,
    STEP_SPACE,
    STEP_VIEW_3D,
    ProjectTreePanel,
)


def test_panel_starts_with_five_steps_all_pending(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    assert panel.count() == 5
    for row in range(panel.count()):
        assert "○" in panel.item(row).text()


def test_step_order_matches_the_workflow(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    texts = [panel.item(row).text() for row in range(panel.count())]
    assert "1." in texts[0]
    assert "2." in texts[1]
    assert "3." in texts[2]
    assert "4." in texts[3]
    assert "5." in texts[4]


def test_clicking_a_step_emits_its_id(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    received: list[str] = []
    panel.step_activated.connect(received.append)

    panel._on_item_clicked(panel.item(1))

    assert received == [STEP_PRODUCTS]


def test_set_step_state_updates_marker(qapp: QApplication) -> None:
    panel = ProjectTreePanel()

    panel.set_step_state(STEP_SPACE, STEP_DONE)
    panel.set_step_state(STEP_PRODUCTS, STEP_CURRENT)

    assert "✓" in panel.item(0).text()
    assert "→" in panel.item(1).text()


def test_set_step_state_ignores_unknown_step(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    # No debe lanzar ni afectar a los pasos reales.
    panel.set_step_state("no-existe", STEP_DONE)
    assert "○" in panel.item(0).text()


def test_all_step_ids_are_wired(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    for step_id in (STEP_SPACE, STEP_PRODUCTS, STEP_OPTIMIZE, STEP_VIEW_3D, STEP_EXPORT):
        panel.set_step_state(step_id, STEP_PENDING)
