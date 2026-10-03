"""Panel de instancias no cargadas: desglose por SKU + detalle por instancia.

`pending_summary_model` (una fila por SKU con pendiente > 0) y `model`
(una fila por instancia concreta, ya existente) leen la misma fuente
--`PackingResult.placements`/`unpacked_units`-- nunca una segunda
fuente de verdad independiente (mejoras UX, Parte 8).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.models.pending_sku_summary_model import (
    COL_NAME as PSUMMARY_COL_NAME,
    COL_PACKED as PSUMMARY_COL_PACKED,
    COL_PENDING as PSUMMARY_COL_PENDING,
    COL_REQUESTED as PSUMMARY_COL_REQUESTED,
    COL_SKU as PSUMMARY_COL_SKU,
    PendingSkuSummaryModel,
)
from cargo_optimizer.presentation.desktop.models.unpacked_table_model import (
    COL_CODE as UNPACKED_COL_CODE,
    COL_INSTANCE as UNPACKED_COL_INSTANCE,
    COL_REASON as UNPACKED_COL_REASON,
    COL_SKU as UNPACKED_COL_SKU,
    UnpackedUnitTableModel,
)
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
        self.summary_table_view.setAlternatingRowColors(False)
        self.summary_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table_view.verticalHeader().setVisible(False)
        self.summary_table_view.setMaximumHeight(220)
        _sh = self.summary_table_view.horizontalHeader()
        _sh.setStretchLastSection(False)
        _sh.setSectionResizeMode(PSUMMARY_COL_SKU, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(PSUMMARY_COL_NAME, QHeaderView.ResizeMode.Stretch)
        _sh.setSectionResizeMode(PSUMMARY_COL_REQUESTED, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(PSUMMARY_COL_PACKED, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(PSUMMARY_COL_PENDING, QHeaderView.ResizeMode.Interactive)
        _sh.resizeSection(PSUMMARY_COL_SKU, 90)
        _sh.resizeSection(PSUMMARY_COL_REQUESTED, 80)
        _sh.resizeSection(PSUMMARY_COL_PACKED, 80)
        _sh.resizeSection(PSUMMARY_COL_PENDING, 80)

        self.model = UnpackedUnitTableModel(self)
        self.table_view = QTableView(self)
        self.table_view.setObjectName("unpackedTableView")
        self.table_view.setModel(self.model)
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.verticalHeader().setVisible(False)
        _uh = self.table_view.horizontalHeader()
        _uh.setStretchLastSection(False)
        _uh.setSectionResizeMode(UNPACKED_COL_SKU, QHeaderView.ResizeMode.Interactive)
        _uh.setSectionResizeMode(UNPACKED_COL_INSTANCE, QHeaderView.ResizeMode.Interactive)
        _uh.setSectionResizeMode(UNPACKED_COL_REASON, QHeaderView.ResizeMode.Stretch)
        _uh.setSectionResizeMode(UNPACKED_COL_CODE, QHeaderView.ResizeMode.Interactive)
        _uh.resizeSection(UNPACKED_COL_SKU, 90)
        _uh.resizeSection(UNPACKED_COL_INSTANCE, 75)
        _uh.resizeSection(UNPACKED_COL_CODE, 100)

        summary_header = QLabel("PENDIENTE POR SKU", self)
        summary_header.setProperty("class", "sectionLabel")
        detail_header = QLabel("DETALLE POR INSTANCIA", self)
        detail_header.setProperty("class", "sectionLabel")

        self.table_view.setMinimumHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_XS)
        layout.addWidget(summary_header)
        layout.addWidget(self.summary_table_view, 1)
        layout.addSpacing(SPACING_XS)
        layout.addWidget(detail_header)
        layout.addWidget(self.table_view, 2)

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
