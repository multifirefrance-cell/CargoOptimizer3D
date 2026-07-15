"""Panel central de productos: `QTableView` sobre `ProductTableModel`.

`QTableView` + `QAbstractTableModel`, nunca `QTableWidget` (ver
`models/product_table_model.py`). Incluye una barra local mínima
("Nuevo producto" / "Eliminar seleccionados") que solo manipula el
modelo Qt en memoria — no hay persistencia todavía.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.presentation.desktop.models.product_table_model import ProductTableModel


class ProductTablePanel(QWidget):
    """Tabla de Load Units con acciones mínimas de alta/baja de filas."""

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

        self._add_button = QPushButton("Nuevo producto", self)
        self._remove_button = QPushButton("Eliminar seleccionados", self)
        self._add_button.clicked.connect(self.model.add_default_product)
        self._remove_button.clicked.connect(self.remove_selected_rows)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._add_button)
        toolbar_layout.addWidget(self._remove_button)
        toolbar_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.table_view)

    def remove_selected_rows(self) -> None:
        rows = {index.row() for index in self.table_view.selectionModel().selectedRows()}
        if rows:
            self.model.remove_rows_at(list(rows))
