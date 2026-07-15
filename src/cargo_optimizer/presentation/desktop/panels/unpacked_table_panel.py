"""Panel de instancias no cargadas: `QTableView` sobre `UnpackedUnitTableModel`."""

from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QTableView, QVBoxLayout, QWidget

from cargo_optimizer.presentation.desktop.models.unpacked_table_model import UnpackedUnitTableModel


class UnpackedTablePanel(QWidget):
    """Tabla de solo lectura con las instancias que quedaron sin cargar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("unpackedTablePanel")

        self.model = UnpackedUnitTableModel(self)

        self.table_view = QTableView(self)
        self.table_view.setObjectName("unpackedTableView")
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table_view)
