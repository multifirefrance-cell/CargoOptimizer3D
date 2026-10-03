"""Panel central de productos: buscador rápido de catálogo + "Lista de carga" simplificada.

Rediseño UX ("workspace operativo"): la operación diaria (agregar un
SKU existente con una cantidad) vive en `ProductQuickAddPanel`, arriba
de la tabla; la tabla misma ("Lista de carga") solo muestra SKU,
Nombre, Cantidad y Peso total — el resto de columnas de
`ProductTableModel` (dimensiones, orientaciones, apilamiento, tipo de
empaque, fragilidad, extintor, color) siguen existiendo en el modelo y
se usan igual en la optimización, pero se ocultan aquí
(`setColumnHidden`) para no saturar la operación diaria: son datos del
catálogo, no de la carga (se editan en "Productos → Catálogo de
productos").

Editar cantidad y eliminar son las únicas dos acciones sobre una línea
ya agregada; nunca reabren el editor completo de producto solo para
cambiar un número. Eliminar siempre pide confirmación antes de quitar
la fila (solo afecta a esta carga; el producto sigue disponible en el
catálogo).
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.icons import icon
from cargo_optimizer.presentation.desktop.models.product_table_model import (
    COL_NAME,
    COL_QUANTITY,
    COL_SKU,
    COL_WEIGHT_TOTAL,
    ProductTableModel,
)
from cargo_optimizer.presentation.desktop.panels.catalog_load_panel import (
    CatalogLoadPanel,
)
from cargo_optimizer.presentation.desktop.style import SPACING_SM, SPACING_XS

_VISIBLE_COLUMNS = frozenset({COL_SKU, COL_NAME, COL_QUANTITY, COL_WEIGHT_TOTAL})
_EMPTY_LOAD_MESSAGE = (
    "No hay productos en esta carga.\n\n"
    "Busque un SKU del catálogo, indique la cantidad y pulse Agregar."
)

_PAGE_EMPTY = 0
_PAGE_TABLE = 1


class ProductTablePanel(QWidget):
    """Buscador de catálogo + "Lista de carga" (solo SKU/Nombre/Cantidad/Peso total)."""

    # Reemite `ProductQuickAddPanel.add_requested` tal cual: este panel no
    # importa `CatalogService` (solo el repositorio de solo-lectura para
    # buscar), así que copiar el `LoadUnit` de catálogo al proyecto (UUID
    # nuevo) lo decide quien conecte esta señal (`MainWindow`, que ya
    # importa `CatalogService` para el flujo "Añadir desde catálogo…").
    add_requested = Signal(object, int)
    optimize_requested = Signal()

    def __init__(
        self, parent: QWidget | None = None, *, repository: ProductCatalogRepository | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("productTablePanel")

        self.model = ProductTableModel(parent=self)
        self.quick_add_panel = CatalogLoadPanel(self, repository=repository)
        self.quick_add_panel.add_requested.connect(self._on_add_requested)

        self.table_view = QTableView(self)
        self.table_view.setObjectName("productTableView")
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(False)  # el color viene del BackgroundRole por producto
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)
        for column in range(self.model.columnCount()):
            self.table_view.setColumnHidden(column, column not in _VISIBLE_COLUMNS)

        header = self.table_view.horizontalHeader()
        # Peso (última visible) se estira para llenar el espacio sobrante;
        # Nombre usa ResizeToContents para que nunca trunque el texto.
        # Todas las ocultas quedan en Fixed para no robar espacio.
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.ResizeToContents)
        header.resizeSection(COL_SKU, 52)
        header.resizeSection(COL_QUANTITY, 40)

        empty_label = QLabel(_EMPTY_LOAD_MESSAGE, self)
        empty_label.setWordWrap(True)
        empty_label.setStyleSheet("color: gray;")
        empty_page = QWidget(self)
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addStretch(1)
        empty_layout.addWidget(empty_label)
        empty_layout.addStretch(1)

        self._stack = QStackedWidget(self)
        self._stack.insertWidget(_PAGE_EMPTY, empty_page)
        self._stack.insertWidget(_PAGE_TABLE, self.table_view)

        self._optimize_button = QPushButton(icon("optimize"), "Optimizar", self)
        self._optimize_button.setProperty("class", "primary")
        self._optimize_button.setToolTip("Ejecutar optimización (F5)")
        self._optimize_button.clicked.connect(self.optimize_requested)

        self._edit_quantity_button = QPushButton("Editar QTY…", self)
        self._remove_button = QPushButton(icon("delete"), "Eliminar", self)
        self._edit_quantity_button.clicked.connect(self._on_edit_quantity_clicked)
        self._remove_button.clicked.connect(self.remove_selected_rows)

        self._load_header_label = QLabel("Lista de carga", self)
        self._load_header_label.setStyleSheet("font-weight: 700; font-size: 10pt;")

        self._update_stack_page()

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        toolbar_layout.setSpacing(SPACING_XS)
        toolbar_layout.addWidget(self._load_header_label, 1)
        toolbar_layout.addWidget(self._optimize_button)
        toolbar_layout.addWidget(self._edit_quantity_button)
        toolbar_layout.addWidget(self._remove_button)

        # quick_add_panel se coloca fuera de este widget (en MainWindow, Area 1).
        # Este panel solo contiene la barra de acciones + la tabla.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(toolbar_layout)
        layout.addWidget(self._stack, 1)

        self.model.rowsInserted.connect(self._update_stack_page)
        self.model.rowsRemoved.connect(self._update_stack_page)
        self.model.modelReset.connect(self._update_stack_page)
        self.model.dataChanged.connect(self._update_stack_page)

    def set_catalog_repository(self, repository: ProductCatalogRepository | None) -> None:
        """Propaga la disponibilidad del catálogo al buscador (modo limitado si es `None`)."""
        self.quick_add_panel.set_repository(repository)

    def _update_stack_page(self, *_args: object) -> None:
        count = self.model.rowCount()
        page = _PAGE_TABLE if count > 0 else _PAGE_EMPTY
        self._stack.setCurrentIndex(page)
        if count > 0:
            self.table_view.resizeColumnToContents(COL_NAME)
            units = self.model.load_units()
            total_weight = sum(u.weight_kg * u.quantity for u in units)
            self._load_header_label.setText(
                f"Lista de carga  ({count})  ·  {total_weight:,.1f} kg".replace(",", ".")
            )
        else:
            self._load_header_label.setText("Lista de carga")

    def _on_add_requested(self, catalog_unit: object, quantity: int) -> None:
        self.add_requested.emit(catalog_unit, quantity)

    def add_units_to_load(self, units: tuple[LoadUnit, ...]) -> None:
        """Añade unidades ya copiadas (UUID nuevo) a la lista de carga."""
        self.model.add_units(units)

    def _selected_row(self) -> int | None:
        rows = {index.row() for index in self.table_view.selectionModel().selectedRows()}
        if len(rows) != 1:
            return None
        return next(iter(rows))

    def _on_edit_quantity_clicked(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._edit_quantity(row)

    def _on_row_double_clicked(self, index: QModelIndex | QPersistentModelIndex) -> None:
        if index.isValid():
            self._edit_quantity(index.row())

    def _edit_quantity(self, row: int) -> None:
        unit = self.model.load_units()[row]
        new_quantity, accepted = QInputDialog.getInt(
            self,
            "Editar QTY",
            f"Nueva cantidad para {unit.sku}:",
            unit.quantity,
            1,
            999_999,
        )
        if not accepted:
            return
        self.model.set_unit_at(row, replace(unit, quantity=new_quantity))

    def remove_selected_rows(self) -> None:
        rows = {index.row() for index in self.table_view.selectionModel().selectedRows()}
        if not rows:
            return
        skus = [self.model.load_units()[row].sku for row in sorted(rows)]
        plural = len(skus) != 1
        response = QMessageBox.question(
            self,
            "Eliminar de la carga",
            f"¿Eliminar {'los' if plural else 'el'} producto{'s' if plural else ''} "
            f"seleccionado{'s' if plural else ''} de esta carga?\n\n"
            + "\n".join(skus)
            + "\n\nEsto solo lo quita de esta carga; seguirá disponible en el catálogo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        self.model.remove_rows_at(list(rows))
