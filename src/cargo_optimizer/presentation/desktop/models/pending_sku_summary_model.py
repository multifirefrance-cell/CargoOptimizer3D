"""`PendingSkuSummaryModel`: desglose de unidades pendientes agrupado por SKU.

Deriva sus filas de los mismos `Placement`/`UnpackedUnit` que ya trae un
`PackingResult` -- nunca recalcula la optimización ni mantiene un
segundo conteo independiente. Solicitado = cargado + pendiente por
construcción (cada instancia aparece en exactamente uno de los dos
conjuntos), así que la suma de "pendiente" de todas las filas siempre
coincide con `PackingResult.unpacked_count`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit

COL_SKU = 0
COL_NAME = 1
COL_REQUESTED = 2
COL_PACKED = 3
COL_PENDING = 4

_HEADERS = ("SKU", "Nombre", "Solicitado", "Cargado", "Pendiente")


class _PendingRow:
    __slots__ = ("sku", "name", "requested", "packed", "pending")

    def __init__(self, sku: str, name: str, requested: int, packed: int, pending: int) -> None:
        self.sku = sku
        self.name = name
        self.requested = requested
        self.packed = packed
        self.pending = pending


class PendingSkuSummaryModel(QAbstractTableModel):
    """Una fila por SKU con unidades pendientes (`pending > 0`), nunca por SKU ya completo."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[_PendingRow] = []

    def set_result(
        self,
        placements: Sequence[Placement],
        unpacked_units: Sequence[UnpackedUnit],
        load_units_by_id: Mapping[UUID, LoadUnit],
    ) -> None:
        packed_counts: Counter[UUID] = Counter(p.load_unit_id for p in placements)
        pending_counts: Counter[UUID] = Counter(u.load_unit_id for u in unpacked_units)

        rows: list[_PendingRow] = []
        for load_unit_id, pending in pending_counts.items():
            if pending <= 0:
                continue
            packed = packed_counts.get(load_unit_id, 0)
            unit = load_units_by_id.get(load_unit_id)
            sku = unit.sku if unit is not None else str(load_unit_id)
            name = unit.name if unit is not None else "—"
            rows.append(_PendingRow(sku, name, packed + pending, packed, pending))
        rows.sort(key=lambda row: row.sku)

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows = []
        self.endResetModel()

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return str(section + 1)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        row = self._rows[index.row()]
        column = index.column()
        if column == COL_SKU:
            return row.sku
        if column == COL_NAME:
            return row.name
        if column == COL_REQUESTED:
            return row.requested
        if column == COL_PACKED:
            return row.packed
        if column == COL_PENDING:
            return row.pending
        return None
