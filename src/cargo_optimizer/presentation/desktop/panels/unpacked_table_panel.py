"""Panel de instancias no cargadas: desglose por SKU + detalle por instancia.

`pending_summary_model` (una fila por SKU con pendiente > 0) y `model`
(una fila por instancia concreta, ya existente) leen la misma fuente
--`PackingResult.placements`/`unpacked_units`-- nunca una segunda
fuente de verdad independiente (mejoras UX, Parte 8).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from PySide6.QtWidgets import QAbstractItemView, QLabel, QTableView, QVBoxLayout, QWidget

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.models.pending_sku_summary_model import (
    PendingSkuSummaryModel,
)
from cargo_optimizer.presentation.desktop.models.unpacked_table_model import UnpackedUnitTableModel
from cargo_optimizer.presentation.desktop.style import SPACING_SM, SPACING_XS


class UnpackedTablePanel(QWidget):
    """Resumen por SKU (arriba) + tabla de solo lectura por instancia (abajo)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("unpackedTablePanel")

        self.pending_summary_model = PendingSkuSummaryModel(self)
        self.summary_table_view = QTableView(self)
        self.summary_table_view.setObjectName("pendingSkuSummaryTableView")
        self.summary_table_view.setModel(self.pending_summary_model)
        self.summary_table_view.setAlternatingRowColors(True)
        self.summary_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table_view.horizontalHeader().setStretchLastSection(True)
        self.summary_table_view.verticalHeader().setVisible(False)
        self.summary_table_view.setMaximumHeight(160)

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
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_XS)
        layout.addWidget(QLabel("<b>PENDIENTE POR SKU</b>", self))
        layout.addWidget(self.summary_table_view)
        layout.addWidget(QLabel("<b>DETALLE POR INSTANCIA</b>", self))
        layout.addWidget(self.table_view, 1)

    def set_result(
        self,
        placements: Sequence[Placement],
        unpacked_units: Sequence[UnpackedUnit],
        load_units_by_id: Mapping[UUID, LoadUnit],
    ) -> None:
        """Actualiza el resumen por SKU y el detalle por instancia a la vez, misma fuente."""
        self.pending_summary_model.set_result(placements, unpacked_units, load_units_by_id)
        self.model.set_unpacked_units(tuple(unpacked_units), load_units_by_id)

    def clear(self) -> None:
        self.pending_summary_model.clear()
        self.model.clear()
