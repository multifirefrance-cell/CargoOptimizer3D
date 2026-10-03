"""`ImportPreviewDialog`: vista previa antes de importar (fase 8.1).

Muestra filas/columnas leídas y la clasificación calculada por
`import_preview.build_catalog_preview` (nuevos/existentes/duplicados/
inválidos) antes de escribir nada en el catálogo, y deja elegir el modo
de importación parcial. Cerrar sin aceptar (Cancelar) aborta toda la
operación.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.infrastructure.excel.import_plan import ImportSelectionMode
from cargo_optimizer.infrastructure.excel.import_preview import CatalogImportPreview

_MODE_LABELS: tuple[tuple[ImportSelectionMode, str], ...] = (
    ("all", "Todas las filas"),
    ("new_only", "Solo productos nuevos"),
    ("updated_only", "Solo productos actualizados"),
    ("valid_only", "Solo productos válidos"),
    ("selected", "Solo filas seleccionadas"),
)
_LABEL_TO_MODE = {label: mode for mode, label in _MODE_LABELS}


class ImportPreviewDialog(QDialog):
    """Diálogo modal de vista previa: contadores + elección del modo de importación."""

    def __init__(self, parent: QWidget | None, *, preview: CatalogImportPreview) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vista previa de la importación")
        self.resize(480, 480)
        self._preview = preview
        self._result_selection_mode: ImportSelectionMode | None = None
        self._result_selected_skus: frozenset[str] | None = None

        form = QFormLayout()
        form.addRow("Filas leídas:", QLabel(str(preview.row_count), self))
        form.addRow("Columnas:", QLabel(str(preview.column_count), self))
        form.addRow("Productos nuevos:", QLabel(str(preview.new_count), self))
        form.addRow("Productos existentes:", QLabel(str(preview.existing_count), self))
        form.addRow("Duplicados en el archivo:", QLabel(str(preview.duplicate_count), self))
        form.addRow("Filas inválidas:", QLabel(str(preview.invalid_count), self))

        self._mode_combo = QComboBox(self)
        self._mode_combo.addItems([label for _mode, label in _MODE_LABELS])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)

        self._selection_list = QListWidget(self)
        self._selection_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for unit in (*preview.new_units, *preview.existing_units):
            item = QListWidgetItem(f"{unit.sku} — {unit.name}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, unit.sku)
            self._selection_list.addItem(item)
        self._selection_list.setVisible(False)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Continuar")
            ok_btn.setProperty("class", "primary")
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Cancelar")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        if preview.invalid_errors or preview.duplicate_errors:
            error_lines = [
                f"Fila {error.row_number}: {error.message}"
                for error in (*preview.duplicate_errors, *preview.invalid_errors)
            ]
            error_label = QLabel(
                "Filas con error (no se importarán):\n" + "\n".join(error_lines[:20]), self
            )
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
        layout.addWidget(QLabel("¿Qué deseas importar?", self))
        layout.addWidget(self._mode_combo)
        layout.addWidget(self._selection_list)
        layout.addWidget(button_box)

    def _on_mode_changed(self, label: str) -> None:
        self._selection_list.setVisible(_LABEL_TO_MODE[label] == "selected")

    def _on_accept(self) -> None:
        mode = _LABEL_TO_MODE[self._mode_combo.currentText()]
        self._result_selection_mode = mode
        if mode == "selected":
            selected: set[str] = set()
            for index in range(self._selection_list.count()):
                item = self._selection_list.item(index)
                if item.checkState() == Qt.CheckState.Checked:
                    selected.add(item.data(Qt.ItemDataRole.UserRole))
            self._result_selected_skus = frozenset(selected)
        self.accept()

    def result_selection_mode(self) -> ImportSelectionMode | None:
        """El modo elegido, o `None` si el usuario canceló la importación."""
        return self._result_selection_mode

    def result_selected_skus(self) -> frozenset[str] | None:
        """Los SKU marcados cuando el modo es "selected"; `None` en cualquier otro modo."""
        return self._result_selected_skus
