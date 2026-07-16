"""Panel izquierdo: árbol de navegación del proyecto.

Muestra las secciones fijas del proyecto (Espacios, Productos,
Resultados, Configuración) sin contenido dinámico debajo — el árbol es
puramente de navegación, no un reflejo en vivo del `CargoProject`
cargado. Seleccionar una sección emite `section_activated` para que
`MainWindow` reaccione: siempre muestra un mensaje en la barra de
estado y, para "Resultados", además navega al panel real
(`MainWindow._on_project_section_activated`).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget

SECTION_PROJECT = "Proyecto"
SECTION_SPACES = "Espacios"
SECTION_PRODUCTS = "Productos"
SECTION_RESULTS = "Resultados"
SECTION_SETTINGS = "Configuración"


class ProjectTreePanel(QTreeWidget):
    """Árbol de secciones del proyecto actual."""

    section_activated = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("projectTree")
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self._build_tree()
        self.itemClicked.connect(self._on_item_clicked)

    def _build_tree(self) -> None:
        root = QTreeWidgetItem([SECTION_PROJECT])
        self.addTopLevelItem(root)
        for section in (SECTION_SPACES, SECTION_PRODUCTS, SECTION_RESULTS, SECTION_SETTINGS):
            root.addChild(QTreeWidgetItem([section]))
        root.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        self.section_activated.emit(item.text(0))
