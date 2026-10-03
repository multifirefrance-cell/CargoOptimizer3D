"""`UnpackedUnitTableModel`: tabla Qt de instancias que no se pudieron cargar.

Cada fila es un `cargo_optimizer.domain.unpacked_unit.UnpackedUnit` real,
tal como lo produce `PackingResult.unpacked_units` — no se reinterpreta
ni se resume nada. `UnpackedUnit` solo guarda `load_unit_id` (UUID), así
que el modelo recibe también el `load_units_by_id` de la misma solicitud
para mostrar el SKU legible en vez del UUID interno.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry

_color_registry = ColorRegistry()

COL_SKU = 0
COL_INSTANCE = 1
COL_REASON = 2
COL_CODE = 3

_HEADERS = ("SKU", "Instancia", "Razón", "Código")


class UnpackedUnitTableModel(QAbstractTableModel):
    """Modelo de solo lectura sobre las `UnpackedUnit` de la última ejecución."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[UnpackedUnit] = []
        self._load_units_by_id: dict[UUID, LoadUnit] = {}
        self._color_cache: dict[str, str] = {}

    def _rebuild_color_cache(self) -> None:
        sku_color_map = {u.sku: u.color_hex for u in self._load_units_by_id.values()}
        self._color_cache = _color_registry.assign_unique_palette_colors(sku_color_map)

    def set_unpacked_units(
        self,
        unpacked_units: tuple[UnpackedUnit, ...],
        load_units_by_id: Mapping[UUID, LoadUnit],
    ) -> None:
        self.beginResetModel()
        self._rows = list(unpacked_units)
        self._load_units_by_id = dict(load_units_by_id)
        self._rebuild_color_cache()
        self.endResetModel()

    def clear(self) -> None:
        self.set_unpacked_units((), {})

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
        if not index.isValid():
            return None
        unpacked = self._rows[index.row()]
        column = index.column()
        load_unit = self._load_units_by_id.get(unpacked.load_unit_id)
        sku = load_unit.sku if load_unit is not None else str(unpacked.load_unit_id)
        resolved = self._color_cache.get(sku, "#CCCCCC")

        if role == Qt.ItemDataRole.DecorationRole and column == COL_SKU:
            return QColor(resolved)

        if role == Qt.ItemDataRole.BackgroundRole:
            color = QColor(resolved)
            color.setAlpha(35)
            return color

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if column == COL_SKU:
            return sku
        if column == COL_INSTANCE:
            return unpacked.instance_number
        if column == COL_REASON:
            return unpacked.reason_message
        if column == COL_CODE:
            return unpacked.reason_code
        return None
