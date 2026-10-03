"""`ProductCatalogDialog`: listar, buscar, editar y reutilizar productos del catálogo (fase 7.1).

`QTableView` + `ProductCatalogTableModel`, nunca `QTableWidget` (mismo
criterio que `ProductTablePanel` desde la fase 5.0). La edición de un
producto siempre pasa por `CatalogProductEditorDialog` — este diálogo
solo orquesta la lista y las llamadas al repositorio.

Desde la fase 8.1 acepta arrastrar y soltar un `.xlsx` directamente
sobre la ventana (``on_excel_dropped``): el diálogo solo detecta el
archivo soltado y delega en el callback — nunca importa nada él mismo.

El botón "Archivar" (antes rotulado, de forma engañosa, "Eliminar")
pide confirmación y llama a `ProductCatalogRepository.archive`
(`is_active=False`): el catálogo nunca borra un registro físicamente
(invariante ya establecida de `CLAUDE.md`) y la interfaz ya no debe
sugerir lo contrario. Un SKU archivado no se destruye: solo se oculta
de la vista por defecto (`_show_archived_check` sin marcar, `_refresh`
filtra a `is_active=True`) y de las búsquedas; marcar "Mostrar
archivados" lo vuelve a mostrar, con la columna "Activo" y el botón
"Restaurar" como única vía para reactivarlo. No existe ninguna acción
de borrado físico: ver el docstring de `_on_archive` para la
justificación completa (sin FK hacia `product_catalog`, pero
irreversible sin ningún beneficio real sobre archivar, que ya libera
el SKU para reutilizarlo).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QModelIndex, QPersistentModelIndex
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QHeaderView,
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
    COL_ACTIVE,
    COL_DIMENSIONS,
    COL_EXTINGUISHER,
    COL_EXTINGUISHER_NOMINAL,
    COL_MAX_STACK,
    COL_NAME,
    COL_PACKAGE_TYPE,
    COL_SKU,
    COL_WEIGHT,
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
        on_sync_induprox: Callable[[], int] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Catálogo de productos")
        self.resize(900, 500)
        self._repository = repository
        self._selected_units_to_add: tuple[LoadUnit, ...] = ()
        self._on_excel_dropped = on_excel_dropped
        self._on_sync_induprox = on_sync_induprox
        self.setAcceptDrops(on_excel_dropped is not None)

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Buscar por SKU o nombre…")
        self._search_edit.textChanged.connect(self._refresh)

        # Por defecto solo se ven los SKU activos -- un SKU archivado
        # (is_active=False) deja de aparecer aquí y no puede confundirse
        # con uno disponible para nuevas cargas. Marcar esta casilla es la
        # única forma de volver a verlos (y de poder "Restaurar" alguno).
        self._show_archived_check = QCheckBox("Mostrar archivados", self)
        self._show_archived_check.toggled.connect(self._refresh)

        self.model = ProductCatalogTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setObjectName("productCatalogTableView")
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(22)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)
        _ch = self.table_view.horizontalHeader()
        _ch.setStretchLastSection(False)
        _ch.setSectionResizeMode(COL_SKU, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        _ch.setSectionResizeMode(COL_DIMENSIONS, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_WEIGHT, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_PACKAGE_TYPE, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_EXTINGUISHER, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_EXTINGUISHER_NOMINAL, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_MAX_STACK, QHeaderView.ResizeMode.Interactive)
        _ch.setSectionResizeMode(COL_ACTIVE, QHeaderView.ResizeMode.Interactive)
        _ch.resizeSection(COL_SKU, 90)
        _ch.resizeSection(COL_DIMENSIONS, 140)
        _ch.resizeSection(COL_WEIGHT, 75)
        _ch.resizeSection(COL_PACKAGE_TYPE, 100)
        _ch.resizeSection(COL_EXTINGUISHER, 65)
        _ch.resizeSection(COL_EXTINGUISHER_NOMINAL, 110)
        _ch.resizeSection(COL_MAX_STACK, 85)
        _ch.resizeSection(COL_ACTIVE, 80)

        self._add_button = QPushButton("Nuevo…", self)
        self._add_button.setToolTip("Crear un nuevo producto en el catálogo")
        self._edit_button = QPushButton("Editar…", self)
        self._edit_button.setToolTip("Editar el producto seleccionado")
        self._duplicate_button = QPushButton("Duplicar…", self)
        self._duplicate_button.setToolTip("Crear una copia del producto seleccionado con un SKU nuevo")
        self._archive_button = QPushButton("Archivar", self)
        self._archive_button.setProperty("class", "warning")
        self._archive_button.setToolTip("Ocultar el producto del catálogo (reversible con Restaurar)")
        self._restore_button = QPushButton("Restaurar", self)
        self._restore_button.setToolTip("Reactivar un producto archivado")
        self._sync_induprox_button = QPushButton("Sincronizar INDUPROX", self)
        self._sync_induprox_button.setToolTip("Agrega al catálogo los SKUs INDUPROX que aún no estén presentes")
        self._sync_induprox_button.setVisible(on_sync_induprox is not None)
        self._add_to_project_button = QPushButton("Añadir seleccionados al proyecto", self)
        self._add_to_project_button.setToolTip("Agregar los productos seleccionados a la carga actual")
        self._add_to_project_button.setProperty("class", "primary")
        self._close_button = QPushButton("Cerrar", self)

        self._add_button.clicked.connect(self._on_add)
        self._edit_button.clicked.connect(self._on_edit)
        self._duplicate_button.clicked.connect(self._on_duplicate)
        self._archive_button.clicked.connect(self._on_archive)
        self._restore_button.clicked.connect(self._on_restore)
        self._sync_induprox_button.clicked.connect(self._on_sync_induprox)
        self._add_to_project_button.clicked.connect(self._on_add_to_project)
        self._close_button.clicked.connect(self.reject)

        self._build_layout()
        self._refresh()

    def _build_layout(self) -> None:
        search_row = QHBoxLayout()
        search_row.addWidget(self._search_edit, 1)
        search_row.addWidget(self._show_archived_check)

        buttons_layout = QHBoxLayout()
        for button in (self._add_button, self._edit_button, self._duplicate_button):
            buttons_layout.addWidget(button)
        _sep = QFrame()
        _sep.setFrameShape(QFrame.Shape.VLine)
        _sep.setFrameShadow(QFrame.Shadow.Sunken)
        buttons_layout.addWidget(_sep)
        for button in (self._archive_button, self._restore_button, self._sync_induprox_button):
            buttons_layout.addWidget(button)
        buttons_layout.addStretch(1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self._add_to_project_button)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
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
        """Recarga la tabla: activos por defecto, o activos+archivados si se pide.

        `ProductCatalogRepository.search` ya filtra a solo activos, así
        que con texto de búsqueda y "Mostrar archivados" marcado hace
        falta filtrar `list_all()` a mano en vez de reutilizar `search` --
        de lo contrario un SKU archivado nunca aparecería aunque el
        usuario pidiera explícitamente verlos.
        """
        text = self._search_edit.text().strip()
        show_archived = self._show_archived_check.isChecked()

        if not show_archived:
            if text:
                entries = tuple(
                    CatalogProductEntry(load_unit=unit, is_active=True)
                    for unit in self._repository.search(text)
                )
            else:
                entries = tuple(
                    CatalogProductEntry(load_unit=unit, is_active=True)
                    for unit in self._repository.list_active()
                )
        else:
            entries = self._repository.list_all()
            if text:
                pattern = text.lower()
                entries = tuple(
                    entry
                    for entry in entries
                    if pattern in entry.load_unit.sku.lower()
                    or pattern in entry.load_unit.name.lower()
                )
        self.model.set_entries(entries)

    def _on_row_double_clicked(self, index: QModelIndex | QPersistentModelIndex) -> None:
        """Doble clic abre el mismo editor que "Editar…" — un solo clic solo selecciona."""
        if index.isValid():
            self._on_edit()

    def _selected_row(self) -> int | None:
        indexes = self.table_view.selectionModel().selectedRows()
        return indexes[0].row() if indexes else None

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table_view.selectionModel().selectedRows()})

    def _on_add(self) -> None:
        existing_colors = tuple(entry.load_unit.color_hex for entry in self._repository.list_all())
        dialog = CatalogProductEditorDialog(self, existing_colors=existing_colors)
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
        """Archiva el SKU seleccionado -- nunca lo borra físicamente.

        No existe una acción de "eliminar definitivamente" en este
        diálogo. Se investigó explícitamente si sería seguro añadirla:
        `product_catalog` no tiene ninguna clave foránea hacia otra tabla
        (ninguna fila de `project_history`/`packing_run_history` referencia
        un id de catálogo) y copiar un producto a un proyecto siempre
        genera un `LoadUnit` con un UUID nuevo (`CatalogService.copy_to_project`),
        así que un `.cargo3d` guardado nunca depende de que una fila del
        catálogo siga existiendo -- un borrado físico no rompería
        ninguna referencia hoy. Aun así no se implementa: sería
        irreversible (a diferencia de "Restaurar") sin aportar ningún
        beneficio real sobre archivar, que ya libera el SKU para
        reutilizarlo (`_check_sku_available` solo mira registros activos)
        y conserva el histórico. Coincide además con el invariante ya
        establecido en `CLAUDE.md`: "Borrado siempre lógico, nunca
        físico". Si en el futuro hiciera falta una purga real (limpieza
        de base de datos, cumplimiento normativo), es una decisión nueva
        con su propio ADR, no una casilla más en este diálogo.
        """
        row = self._selected_row()
        if row is None:
            return
        entry = self.model.entry_at(row)
        response = QMessageBox.question(
            self,
            "Archivar producto",
            f"¿Archivar '{entry.load_unit.sku}' del catálogo?\n\n"
            "Dejará de estar disponible para agregarlo a nuevos proyectos, pero su "
            'histórico se conserva y podrás restaurarlo más tarde con "Restaurar" '
            '(marca "Mostrar archivados" para volver a verlo en esta lista).',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
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

    def _on_sync_induprox(self) -> None:
        if self._on_sync_induprox is None:
            return
        changes = self._on_sync_induprox()
        if changes == 0:
            QMessageBox.information(self, "Sin cambios", "El catálogo ya está sincronizado con los SKUs INDUPROX.")
        else:
            QMessageBox.information(
                self, "Sincronización completada",
                f"Catálogo actualizado: {changes} cambio(s) aplicados.\n"
                "Los productos no INDUPROX fueron archivados y los SKUs faltantes fueron agregados."
            )
        self._refresh()
