"""`ColumnMappingDialog`: asistente de mapeo de columnas de Excel (fase 8.1).

Muestra cada cabecera del archivo elegido junto a un desplegable con el
campo del sistema que le corresponde (ya con la detección automática de
`mapping.detect_column_mapping` preseleccionada); las cabeceras no
reconocidas quedan en "(Ignorar)" hasta que el usuario las asigna a
mano. Permite aplicar y guardar perfiles de mapeo reutilizables
(`ImportMappingProfileRepository`, fase 8.1).
"""

from __future__ import annotations

from contextlib import suppress

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import ImportMappingProfileRepository
from cargo_optimizer.infrastructure.excel.detection import TemplateKind
from cargo_optimizer.infrastructure.excel.mapping import canonical_columns_for

_IGNORE_LABEL = "(Ignorar)"


class ColumnMappingDialog(QDialog):
    """Asistente modal: asigna cada cabecera del archivo a un campo del sistema o la ignora."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        target_kind: TemplateKind,
        source_headers: tuple[str, ...],
        detected_mapping: dict[str, str],
        profile_repository: ImportMappingProfileRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mapeo de columnas")
        self.resize(600, 450)
        self._target_kind = target_kind
        self._source_headers = source_headers
        self._profile_repository = profile_repository
        self._canonical_options = (_IGNORE_LABEL, *canonical_columns_for(target_kind))
        self._result_mapping: dict[str, str] | None = None

        self._table = QTableWidget(len(source_headers), 2, self)
        self._table.setHorizontalHeaderLabels(["Columna del archivo", "Campo del sistema"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._combos: list[QComboBox] = []
        for row, header in enumerate(source_headers):
            self._table.setItem(row, 0, QTableWidgetItem(header))
            combo = QComboBox(self)
            combo.addItems(self._canonical_options)
            canonical = detected_mapping.get(header)
            if canonical is not None and canonical in self._canonical_options:
                combo.setCurrentText(canonical)
            else:
                combo.setCurrentText(_IGNORE_LABEL)
            self._table.setCellWidget(row, 1, combo)
            self._combos.append(combo)

        self._load_profile_combo = QComboBox(self)
        self._load_profile_combo.addItem("Elegir perfil guardado…", None)
        if profile_repository is not None:
            for entry in profile_repository.list_active(target_kind):
                self._load_profile_combo.addItem(entry.name, entry.id)
        self._load_profile_combo.currentIndexChanged.connect(self._on_profile_chosen)

        self._save_button = QPushButton("Guardar como perfil…", self)
        self._save_button.clicked.connect(self._on_save_profile)
        self._save_button.setEnabled(profile_repository is not None)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Perfil guardado:", self))
        profile_row.addWidget(self._load_profile_combo, 1)
        profile_row.addWidget(self._save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(profile_row)
        layout.addWidget(
            QLabel(
                "Asigna cada columna del archivo a un campo del sistema. "
                "Las columnas marcadas '(Ignorar)' no se importarán.",
                self,
            )
        )
        layout.addWidget(self._table)
        layout.addWidget(button_box)

    def _on_profile_chosen(self, index: int) -> None:
        if self._profile_repository is None:
            return
        profile_id = self._load_profile_combo.itemData(index)
        if profile_id is None:
            return
        entry = self._profile_repository.get_by_id(profile_id)
        if entry is None:
            return
        for row, header in enumerate(self._source_headers):
            canonical = entry.column_mapping.get(header)
            combo = self._combos[row]
            if canonical is not None and canonical in self._canonical_options:
                combo.setCurrentText(canonical)
        with suppress(RepositoryError):
            self._profile_repository.touch_last_used(entry.id)

    def _on_save_profile(self) -> None:
        if self._profile_repository is None:
            return
        name, accepted = QInputDialog.getText(self, "Guardar perfil de mapeo", "Nombre del perfil:")
        if not accepted or not name.strip():
            return
        try:
            self._profile_repository.add(name.strip(), self._target_kind, self._current_mapping())
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo guardar el perfil", str(exc))
            return
        QMessageBox.information(self, "Perfil guardado", f"Perfil '{name.strip()}' guardado.")

    def _current_mapping(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for header, combo in zip(self._source_headers, self._combos, strict=True):
            chosen = combo.currentText()
            if chosen != _IGNORE_LABEL:
                mapping[header] = chosen
        return mapping

    def _on_accept(self) -> None:
        self._result_mapping = self._current_mapping()
        self.accept()

    def result_mapping(self) -> dict[str, str] | None:
        """El mapeo elegido (cabecera del archivo -> columna canónica), o `None` si se canceló."""
        return self._result_mapping
