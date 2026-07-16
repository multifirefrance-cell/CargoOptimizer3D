"""Panel izquierdo: guía de flujo de 5 pasos (rediseño UX, no un árbol de secciones).

El árbol de navegación original (fase 5.0) no aportaba valor real: era
una lista estática de 4 secciones fijas sin contenido dinámico, que
solo mostraba un mensaje en la barra de estado al hacer clic — nunca
reflejaba en qué punto del trabajo estaba realmente el usuario. Este
panel lo sustituye por una guía de 5 pasos ("Espacio de carga" →
"Productos" → "Optimizar" → "Ver resultado 3D" → "Exportar") con un
estado real (pendiente/actual/hecho) que `MainWindow` recalcula cada
vez que cambia el espacio, los productos, el resultado o se exporta —
exactamente el "FLUJO NUEVO" pedido en la auditoría UX. Sigue siendo un
widget de navegación puro: no conoce `PackingEngine` ni el estado real
del proyecto por sí mismo, `MainWindow` se lo indica con
`set_step_state`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

STEP_SPACE = "space"
STEP_PRODUCTS = "products"
STEP_OPTIMIZE = "optimize"
STEP_VIEW_3D = "view_3d"
STEP_EXPORT = "export"

STEP_PENDING = "pending"
STEP_CURRENT = "current"
STEP_DONE = "done"

_STEP_LABELS: dict[str, str] = {
    STEP_SPACE: "1. Espacio de carga",
    STEP_PRODUCTS: "2. Productos",
    STEP_OPTIMIZE: "3. Optimizar",
    STEP_VIEW_3D: "4. Ver resultado 3D",
    STEP_EXPORT: "5. Exportar",
}

_STEP_ORDER = (STEP_SPACE, STEP_PRODUCTS, STEP_OPTIMIZE, STEP_VIEW_3D, STEP_EXPORT)

_MARKER_BY_STATE = {
    STEP_PENDING: "○",
    STEP_CURRENT: "→",
    STEP_DONE: "✓",
}


class ProjectTreePanel(QListWidget):
    """Guía de los 5 pasos del flujo principal, con estado pendiente/actual/hecho."""

    step_activated = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowStepsList")
        self.setFrameShape(QListWidget.Shape.NoFrame)
        self._items: dict[str, QListWidgetItem] = {}
        self._build_steps()
        self.itemClicked.connect(self._on_item_clicked)

    def _build_steps(self) -> None:
        for step_id in _STEP_ORDER:
            item = QListWidgetItem(self)
            item.setData(Qt.ItemDataRole.UserRole, step_id)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._items[step_id] = item
            self.set_step_state(step_id, STEP_PENDING)

    def set_step_state(self, step_id: str, state: str) -> None:
        """Actualiza el marcador/énfasis visual de un paso (lo decide `MainWindow`)."""
        item = self._items.get(step_id)
        if item is None:
            return
        marker = _MARKER_BY_STATE.get(state, _MARKER_BY_STATE[STEP_PENDING])
        item.setText(f"{marker}  {_STEP_LABELS[step_id]}")
        font = QFont(item.font())
        font.setBold(state == STEP_CURRENT)
        font.setPointSize(font.pointSize() + (1 if state == STEP_CURRENT else 0))
        item.setFont(font)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        step_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(step_id, str):
            self.step_activated.emit(step_id)
