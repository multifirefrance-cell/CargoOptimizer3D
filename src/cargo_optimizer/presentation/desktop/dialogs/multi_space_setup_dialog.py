"""`MultiSpaceSetupDialog`: elegir y ordenar candidatos para OPT-01, y fijar `max_spaces`.

Los candidatos disponibles son el espacio de carga actual del
formulario (si es válido) más los perfiles activos del catálogo (si el
catálogo está disponible — en modo limitado solo se ofrece el espacio
actual). El orden en la lista "Seleccionados" es el orden de
preferencia que `MultiSpaceAssignmentRequest.loading_space_candidates`
usa tal cual (ver `docs/MultiSpaceAssignment.md`).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.loading_space import LoadingSpace

_CURRENT_SPACE_SUFFIX = " (espacio actual)"


class MultiSpaceSetupDialog(QDialog):
    """Diálogo modal: candidatos ordenados + `max_spaces` para una asignación multi-espacio."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        current_space: LoadingSpace | None,
        catalog_profiles: tuple[LoadingSpace, ...],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Optimización multi-espacio")
        self.resize(650, 420)
        self._result_candidates: tuple[LoadingSpace, ...] = ()
        self._result_max_spaces: int | None = None

        self._available_list = QListWidget(self)
        self._available_list.setObjectName("multiSpaceAvailableList")
        if current_space is not None:
            self._add_available_item(current_space, suffix=_CURRENT_SPACE_SUFFIX)
        for profile in catalog_profiles:
            self._add_available_item(profile)

        self._selected_list = QListWidget(self)
        self._selected_list.setObjectName("multiSpaceSelectedList")

        self._add_button = QPushButton("Añadir »", self)
        self._remove_button = QPushButton("« Quitar", self)
        self._move_up_button = QPushButton("Subir", self)
        self._move_down_button = QPushButton("Bajar", self)

        self._add_button.clicked.connect(self._on_add)
        self._remove_button.clicked.connect(self._on_remove)
        self._move_up_button.clicked.connect(self._on_move_up)
        self._move_down_button.clicked.connect(self._on_move_down)

        self._limit_check = QCheckBox("Limitar cantidad máxima de espacios", self)
        self._limit_check.toggled.connect(self._on_limit_toggled)
        self._max_spaces_spin = QSpinBox(self)
        self._max_spaces_spin.setRange(1, 999)
        self._max_spaces_spin.setValue(10)
        self._max_spaces_spin.setEnabled(False)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setProperty("class", "primary")

        self._build_layout()

    def _add_available_item(self, space: LoadingSpace, *, suffix: str = "") -> None:
        item = QListWidgetItem(f"{space.name}{suffix}")
        item.setData(Qt.ItemDataRole.UserRole, space)
        self._available_list.addItem(item)

    def _build_layout(self) -> None:
        lists_layout = QHBoxLayout()

        available_column = QVBoxLayout()
        available_column.addWidget(QLabel("Espacios disponibles", self))
        available_column.addWidget(self._available_list)
        lists_layout.addLayout(available_column)

        buttons_column = QVBoxLayout()
        buttons_column.addStretch(1)
        buttons_column.addWidget(self._add_button)
        buttons_column.addWidget(self._remove_button)
        buttons_column.addSpacing(16)
        buttons_column.addWidget(self._move_up_button)
        buttons_column.addWidget(self._move_down_button)
        buttons_column.addStretch(1)
        lists_layout.addLayout(buttons_column)

        selected_column = QVBoxLayout()
        selected_column.addWidget(QLabel("Seleccionados (orden de preferencia)", self))
        selected_column.addWidget(self._selected_list)
        lists_layout.addLayout(selected_column)

        limit_layout = QHBoxLayout()
        limit_layout.addWidget(self._limit_check)
        limit_layout.addWidget(self._max_spaces_spin)
        limit_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(lists_layout)
        layout.addLayout(limit_layout)
        layout.addWidget(self._button_box)

    def _on_limit_toggled(self, checked: bool) -> None:
        self._max_spaces_spin.setEnabled(checked)

    def _on_add(self) -> None:
        for item in self._available_list.selectedItems():
            space = item.data(Qt.ItemDataRole.UserRole)
            moved = QListWidgetItem(item.text())
            moved.setData(Qt.ItemDataRole.UserRole, space)
            self._selected_list.addItem(moved)

    def _on_remove(self) -> None:
        for item in self._selected_list.selectedItems():
            self._selected_list.takeItem(self._selected_list.row(item))

    def _on_move_up(self) -> None:
        row = self._selected_list.currentRow()
        if row <= 0:
            return
        item = self._selected_list.takeItem(row)
        self._selected_list.insertItem(row - 1, item)
        self._selected_list.setCurrentRow(row - 1)

    def _on_move_down(self) -> None:
        row = self._selected_list.currentRow()
        if row < 0 or row >= self._selected_list.count() - 1:
            return
        item = self._selected_list.takeItem(row)
        self._selected_list.insertItem(row + 1, item)
        self._selected_list.setCurrentRow(row + 1)

    def _on_accept(self) -> None:
        candidates = tuple(
            self._selected_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._selected_list.count())
        )
        if not candidates:
            self._selected_list.setToolTip("Selecciona al menos un espacio candidato.")
            return
        self._result_candidates = candidates
        self._result_max_spaces = (
            self._max_spaces_spin.value() if self._limit_check.isChecked() else None
        )
        self.accept()

    def result_candidates(self) -> tuple[LoadingSpace, ...]:
        """Candidatos en el orden de preferencia elegido, o `()` si se canceló."""
        return self._result_candidates

    def result_max_spaces(self) -> int | None:
        return self._result_max_spaces
