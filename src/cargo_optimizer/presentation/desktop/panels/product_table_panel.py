"""Panel central de productos: `QTableView` sobre `ProductTableModel`.

`QTableView` + `QAbstractTableModel`, nunca `QTableWidget` (ver
`models/product_table_model.py`). Incluye una barra local
("Nuevo producto…" / "Editar…" / "Eliminar seleccionados") que solo
manipula el modelo Qt en memoria; el panel en sí no persiste nada — es
`MainWindow` quien vuelca el modelo a `.cargo3d` (fase 7.0, ver
`docs/ProjectFiles.md`) cuando el usuario guarda el proyecto.

"Nuevo producto…"/"Editar…" abren `CatalogProductEditorDialog` (un
formulario dedicado con etiquetas, en vez de insertar una fila en
blanco para editarla celda a celda): la tabla queda como vista de
conjunto y edición rápida de campos sueltos, no como el único punto de
alta de un producto — encontrado como fricción real en la auditoría
de estabilización de la Beta 1.0.
"""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.presentation.desktop.dialogs.catalog_product_editor_dialog import (
    CatalogProductEditorDialog,
)
from cargo_optimizer.presentation.desktop.models.product_table_model import ProductTableModel


class ProductTablePanel(QWidget):
    """Tabla de Load Units con acciones de alta/edición/baja de filas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("productTablePanel")

        self.model = ProductTableModel(parent=self)

        self.table_view = QTableView(self)
        self.table_view.setObjectName("productTableView")
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)

        self._add_button = QPushButton("Nuevo producto…", self)
        self._edit_button = QPushButton("Editar…", self)
        self._remove_button = QPushButton("Eliminar seleccionados", self)
        self._add_button.clicked.connect(self._on_add_product)
        self._edit_button.clicked.connect(self._on_edit_selected_product)
        self._remove_button.clicked.connect(self.remove_selected_rows)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._add_button)
        toolbar_layout.addWidget(self._edit_button)
        toolbar_layout.addWidget(self._remove_button)
        toolbar_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.table_view)

    def _on_add_product(self) -> None:
        dialog = CatalogProductEditorDialog(self, title="Nuevo producto")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        unit = dialog.result_load_unit()
        if unit is not None:
            self.model.add_units((unit,))

    def _selected_row(self) -> int | None:
        rows = {index.row() for index in self.table_view.selectionModel().selectedRows()}
        if len(rows) != 1:
            return None
        return next(iter(rows))

    def _on_edit_selected_product(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._edit_row(row)

    def _on_row_double_clicked(self, index: QModelIndex | QPersistentModelIndex) -> None:
        if index.isValid():
            self._edit_row(index.row())

    def _edit_row(self, row: int) -> None:
        unit = self.model.load_units()[row]
        dialog = CatalogProductEditorDialog(
            self, load_unit=unit, title_when_editing="Editar producto"
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.result_load_unit()
        if updated is not None:
            self.model.set_unit_at(row, updated)

    def remove_selected_rows(self) -> None:
        rows = {index.row() for index in self.table_view.selectionModel().selectedRows()}
        if rows:
            self.model.remove_rows_at(list(rows))
