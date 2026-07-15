"""Pruebas de `ProjectTreePanel`."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.presentation.desktop.panels.project_tree_panel import (
    SECTION_PRODUCTS,
    SECTION_PROJECT,
    SECTION_RESULTS,
    SECTION_SETTINGS,
    SECTION_SPACES,
    ProjectTreePanel,
)


def test_tree_has_project_root_and_four_sections(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    assert panel.topLevelItemCount() == 1
    root = panel.topLevelItem(0)
    assert root.text(0) == SECTION_PROJECT
    assert root.childCount() == 4
    children = {root.child(i).text(0) for i in range(root.childCount())}
    assert children == {SECTION_SPACES, SECTION_PRODUCTS, SECTION_RESULTS, SECTION_SETTINGS}


def test_clicking_a_section_emits_signal(qapp: QApplication) -> None:
    panel = ProjectTreePanel()
    received: list[str] = []
    panel.section_activated.connect(received.append)

    root = panel.topLevelItem(0)
    products_item = next(
        root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == SECTION_PRODUCTS
    )
    panel._on_item_clicked(products_item, 0)

    assert received == [SECTION_PRODUCTS]
