"""`ProductCatalogDialog`: listar, buscar, editar y reutilizar productos del catálogo (fase 7.1).

`QTableView` + `ProductCatalogTableModel`, nunca `QTableWidget` (mismo
criterio que `ProductTablePanel` desde la fase 5.0). La edición de un
producto siempre pasa por `CatalogProductEditorDialog` — este diálogo
solo orquesta la lista y las llamadas al repositorio.

Desde la fase 8.1 acepta arrastrar y soltar un `.xlsx` directamente
sobre la ventana (``on_excel_dropped``): el diálogo solo detecta el
archivo soltado y delega en el callback — nunca importa nada él mismo.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import (
    CatalogProductEntry,
    ProductCatalogRepository,
)
from cargo_optimizer.presentation.desktop.dialogs.catalog_product_editor_dialog import (
    CatalogProductEditorDialog,
)
from cargo_optimizer.presentation.desktop.drag_drop import first_excel_path, has_excel_url
from cargo_optimizer.presentation.desktop.models.product_catalog_table_model import (
    ProductCatalogTableModel,
)


class ProductCatalogDialog(QDialog):
    """Diálogo modal del catálogo de productos: listar/buscar/CRUD/añadir al proyecto."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        repository: ProductCatalogRepository,
        on_excel_dropped: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Catálogo de productos")
        self.resize(900, 500)
        self._repository = repository
        self._selected_units_to_add: tuple[LoadUnit, ...] = ()
        self._on_excel_dropped = on_excel_dropped
        self.setAcceptDrops(on_excel_dropped is not None)

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Buscar por SKU o nombre…")
        self._search_edit.textChanged.connect(self._refresh)

        self.model = ProductCatalogTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setObjectName("productCatalogTableView")
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)

        self._add_button = QPushButton("Nuevo…", self)
        self._edit_button = QPushButton("Editar…", self)
        self._duplicate_button = QPushButton("Duplicar…", self)
        self._archive_button = QPushButton("Archivar", self)
        self._restore_button = QPushButton("Restaurar", self)
        self._add_to_project_button = QPushButton("Añadir seleccionados al proyecto", self)
        self._close_button = QPushButton("Cerrar", self)

        self._add_button.clicked.connect(self._on_add)
        self._edit_button.clicked.connect(self._on_edit)
        self._duplicate_button.clicked.connect(self._on_duplicate)
        self._archive_button.clicked.connect(self._on_archive)
        self._restore_button.clicked.connect(self._on_restore)
        self._add_to_project_button.clicked.connect(self._on_add_to_project)
        self._close_button.clicked.connect(self.reject)

        self._build_layout()
        self._refresh()

    def _build_layout(self) -> None:
        buttons_layout = QHBoxLayout()
        for button in (
            self._add_button,
            self._edit_button,
            self._duplicate_button,
            self._archive_button,
            self._restore_button,
        ):
            buttons_layout.addWidget(button)
        buttons_layout.addStretch(1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self._add_to_project_button)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_edit)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table_view)
        layout.addLayout(bottom_layout)

    def refresh(self) -> None:
        """Vuelve a leer el catálogo (p. ej. tras una importación por arrastrar y soltar)."""
        self._refresh()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if self._on_excel_dropped is not None and has_excel_url(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        path = first_excel_path(event)
        if path is None or self._on_excel_dropped is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self._on_excel_dropped(path)

    def _refresh(self) -> None:
        text = self._search_edit.text().strip()
        if text:
            entries = tuple(
                CatalogProductEntry(load_unit=unit, is_active=True)
                for unit in self._repository.search(text)
            )
        else:
            entries = self._repository.list_all()
        self.model.set_entries(entries)

    def _selected_row(self) -> int | None:
        indexes = self.table_view.selectionModel().selectedRows()
        return indexes[0].row() if indexes else None

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table_view.selectionModel().selectedRows()})

    def _on_add(self) -> None:
        dialog = CatalogProductEditorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        unit = dialog.result_load_unit()
        if unit is None:
            return
        try:
            self._repository.add(unit)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo agregar el producto", str(exc))
        self._refresh()

    def _on_edit(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        entry = self.model.entry_at(row)
        dialog = CatalogProductEditorDialog(self, load_unit=entry.load_unit)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        unit = dialog.result_load_unit()
        if unit is None:
            return
        try:
            self._repository.update(unit)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo actualizar el producto", str(exc))
        self._refresh()

    def _on_duplicate(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        entry = self.model.entry_at(row)
        new_sku, accepted = QInputDialog.getText(
            self,
            "Duplicar producto",
            "SKU del nuevo producto:",
            text=f"{entry.load_unit.sku}-COPIA",
        )
        if not accepted or not new_sku.strip():
            return
        try:
            self._repository.duplicate(entry.load_unit.id, new_sku.strip())
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo duplicar el producto", str(exc))
        self._refresh()

    def _on_archive(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        entry = self.model.entry_at(row)
        try:
            self._repository.archive(entry.load_unit.id)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo archivar el producto", str(exc))
        self._refresh()

    def _on_restore(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        entry = self.model.entry_at(row)
        try:
            self._repository.restore(entry.load_unit.id)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo restaurar el producto", str(exc))
        self._refresh()

    def _on_add_to_project(self) -> None:
        rows = self._selected_rows()
        if not rows:
            QMessageBox.information(
                self, "Sin selección", "Selecciona al menos un producto para añadir al proyecto."
            )
            return
        self._selected_units_to_add = tuple(self.model.entry_at(row).load_unit for row in rows)
        self.accept()

    def selected_units_to_add(self) -> tuple[LoadUnit, ...]:
        """Los `LoadUnit` elegidos al pulsar "Añadir al proyecto", o `()` si se canceló."""
        return self._selected_units_to_add
