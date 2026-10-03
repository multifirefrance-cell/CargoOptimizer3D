"""`LoadingSpaceProfilesDialog`: listar, buscar, editar y aplicar perfiles de espacio (fase 7.1).

Los perfiles integrados (`is_builtin=True`) nunca se sobrescriben
directamente: `_on_edit` los abre en modo "duplicar como personalizado"
en vez de permitir `update()` (que el repositorio rechaza de todas
formas — ver `LoadingSpaceProfileRepository.update`).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
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

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import (
    LoadingSpaceProfileEntry,
    LoadingSpaceProfileRepository,
)
from cargo_optimizer.presentation.desktop.dialogs.loading_space_profile_editor_dialog import (
    LoadingSpaceProfileEditorDialog,
)
from cargo_optimizer.presentation.desktop.models.loading_space_profile_table_model import (
    COL_CATEGORY,
    COL_DIMENSIONS,
    COL_DOOR_POSITION,
    COL_MAX_WEIGHT,
    COL_NAME,
    COL_ORIGIN,
    LoadingSpaceProfileTableModel,
)


class LoadingSpaceProfilesDialog(QDialog):
    """Diálogo modal de perfiles de espacio: listar/buscar/CRUD/aplicar al proyecto."""

    def __init__(
        self, parent: QWidget | None, *, repository: LoadingSpaceProfileRepository
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Perfiles de espacio de carga")
        self.resize(750, 450)
        self._repository = repository
        self._result_space: LoadingSpace | None = None

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Buscar por nombre…")
        self._search_edit.textChanged.connect(self._refresh)

        self.model = LoadingSpaceProfileTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setObjectName("loadingSpaceProfilesTableView")
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.verticalHeader().setVisible(False)
        _ph = self.table_view.horizontalHeader()
        _ph.setStretchLastSection(False)
        _ph.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        _ph.setSectionResizeMode(COL_CATEGORY, QHeaderView.ResizeMode.Interactive)
        _ph.setSectionResizeMode(COL_DIMENSIONS, QHeaderView.ResizeMode.Interactive)
        _ph.setSectionResizeMode(COL_MAX_WEIGHT, QHeaderView.ResizeMode.Interactive)
        _ph.setSectionResizeMode(COL_DOOR_POSITION, QHeaderView.ResizeMode.Interactive)
        _ph.setSectionResizeMode(COL_ORIGIN, QHeaderView.ResizeMode.Interactive)
        _ph.resizeSection(COL_CATEGORY, 100)
        _ph.resizeSection(COL_DIMENSIONS, 160)
        _ph.resizeSection(COL_MAX_WEIGHT, 110)
        _ph.resizeSection(COL_DOOR_POSITION, 80)
        _ph.resizeSection(COL_ORIGIN, 80)

        self._add_button = QPushButton("Nuevo…", self)
        self._edit_button = QPushButton("Editar…", self)
        self._duplicate_button = QPushButton("Duplicar…", self)
        self._archive_button = QPushButton("Archivar", self)
        self._restore_button = QPushButton("Restaurar", self)
        self._apply_button = QPushButton("Aplicar al proyecto", self)
        self._apply_button.setProperty("class", "primary")
        self._close_button = QPushButton("Cerrar", self)

        self._add_button.clicked.connect(self._on_add)
        self._edit_button.clicked.connect(self._on_edit)
        self._duplicate_button.clicked.connect(self._on_duplicate)
        self._archive_button.clicked.connect(self._on_archive)
        self._restore_button.clicked.connect(self._on_restore)
        self._apply_button.clicked.connect(self._on_apply)
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
        bottom_layout.addWidget(self._apply_button)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self._close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search_edit)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table_view)
        layout.addLayout(bottom_layout)

    def _refresh(self) -> None:
        text = self._search_edit.text().strip()
        entries = self._repository.search(text) if text else self._repository.list_all()
        self.model.set_entries(entries)

    def _selected_entry(self) -> LoadingSpaceProfileEntry | None:
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.model.entry_at(indexes[0].row())

    def _on_add(self) -> None:
        dialog = LoadingSpaceProfileEditorDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        space = dialog.result_space()
        if space is None:
            return
        try:
            self._repository.add(space)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo guardar el perfil", str(exc))
        self._refresh()

    def _on_edit(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if entry.is_builtin:
            QMessageBox.information(
                self,
                "Perfil integrado",
                "Los perfiles integrados no se pueden modificar directamente. "
                "Usa 'Duplicar…' para crear una copia personalizada editable.",
            )
            return
        dialog = LoadingSpaceProfileEditorDialog(self, space=entry.loading_space)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        space = dialog.result_space()
        if space is None:
            return
        try:
            self._repository.update(space)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo actualizar el perfil", str(exc))
        self._refresh()

    def _on_duplicate(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        new_name, accepted = QInputDialog.getText(
            self,
            "Duplicar perfil",
            "Nombre del nuevo perfil:",
            text=f"{entry.loading_space.name} (copia)",
        )
        if not accepted or not new_name.strip():
            return
        try:
            self._repository.duplicate(entry.loading_space.id, new_name.strip())
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo duplicar el perfil", str(exc))
        self._refresh()

    def _on_archive(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if entry.is_builtin:
            QMessageBox.information(
                self,
                "Perfil integrado",
                "Los perfiles integrados no se pueden archivar directamente. "
                "Usa 'Duplicar…' para crear una copia personalizada archivable.",
            )
            return
        try:
            self._repository.archive(entry.loading_space.id)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo archivar el perfil", str(exc))
        self._refresh()

    def _on_restore(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        try:
            self._repository.restore(entry.loading_space.id)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo restaurar el perfil", str(exc))
        self._refresh()

    def _on_apply(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un perfil para aplicarlo.")
            return
        self._result_space = entry.loading_space
        self.accept()

    def result_space(self) -> LoadingSpace | None:
        """El perfil elegido al pulsar "Aplicar al proyecto", o `None` si se canceló."""
        return self._result_space
