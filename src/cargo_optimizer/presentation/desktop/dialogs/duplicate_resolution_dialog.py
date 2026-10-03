"""`DuplicateResolutionDialog`: resolver SKU ya existentes al importar (fase 8.1).

Por cada `LoadUnit` cuyo SKU ya existe en el catálogo, el usuario elige
Actualizar/Duplicar/Ignorar, fila a fila o de una vez con "Aplicar a
todos". Cerrar el diálogo sin aceptar (Cancelar) equivale a abortar la
importación completa — el llamador nunca aplica un `ImportPlan` cuando
`exec()` no devuelve `Accepted`.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.excel.import_plan import DuplicateResolution

_ACTION_LABELS: tuple[tuple[DuplicateResolution, str], ...] = (
    ("update", "Actualizar"),
    ("duplicate", "Duplicar"),
    ("ignore", "Ignorar"),
)
_LABEL_TO_ACTION = {label: action for action, label in _ACTION_LABELS}
_ACTION_LABEL_TEXTS = tuple(label for _action, label in _ACTION_LABELS)


class DuplicateResolutionDialog(QDialog):
    """Diálogo modal: qué hacer con cada SKU que ya existe en el catálogo."""

    def __init__(self, parent: QWidget | None, *, existing_units: tuple[LoadUnit, ...]) -> None:
        super().__init__(parent)
        self.setWindowTitle("SKU ya existentes en el catálogo")
        self.resize(520, 400)
        self._existing_units = existing_units
        self._result_resolutions: dict[str, DuplicateResolution] | None = None

        self._table = QTableWidget(len(existing_units), 3, self)
        self._table.setHorizontalHeaderLabels(["SKU", "Nombre", "Acción"])
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setVisible(False)
        _dh = self._table.horizontalHeader()
        _dh.setStretchLastSection(False)
        _dh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        _dh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _dh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        _dh.resizeSection(0, 90)
        _dh.resizeSection(2, 120)
        self._action_combos: list[QComboBox] = []
        for row, unit in enumerate(existing_units):
            self._table.setItem(row, 0, QTableWidgetItem(unit.sku))
            self._table.setItem(row, 1, QTableWidgetItem(unit.name))
            combo = QComboBox(self)
            combo.addItems(_ACTION_LABEL_TEXTS)
            self._table.setCellWidget(row, 2, combo)
            self._action_combos.append(combo)

        self._apply_all_combo = QComboBox(self)
        self._apply_all_combo.addItems(_ACTION_LABEL_TEXTS)
        self._apply_all_button = QPushButton("Aplicar a todos", self)
        self._apply_all_button.clicked.connect(self._on_apply_all)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setProperty("class", "primary")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        apply_all_row = QHBoxLayout()
        apply_all_row.addWidget(self._apply_all_combo)
        apply_all_row.addWidget(self._apply_all_button)
        apply_all_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"{len(existing_units)} producto(s) del archivo ya existen en el catálogo "
                "por su SKU. Elige qué hacer con cada uno:",
                self,
            )
        )
        layout.addWidget(self._table)
        layout.addLayout(apply_all_row)
        layout.addWidget(button_box)

    def _on_apply_all(self) -> None:
        chosen = self._apply_all_combo.currentText()
        for combo in self._action_combos:
            combo.setCurrentText(chosen)

    def _on_accept(self) -> None:
        self._result_resolutions = {
            unit.sku: _LABEL_TO_ACTION[combo.currentText()]
            for unit, combo in zip(self._existing_units, self._action_combos, strict=True)
        }
        self.accept()

    def result_resolutions(self) -> dict[str, DuplicateResolution] | None:
        """``{sku: accion}`` elegido, o `None` si el usuario canceló la importación."""
        return self._result_resolutions
