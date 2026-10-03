"""`ProductCatalogTableModel`: tabla de solo lectura sobre el catálogo de productos (fase 7.1).

Sobre `CatalogProductEntry` (no `LoadUnit` directo), para poder mostrar
la columna "Activo" — `QAbstractTableModel`, nunca `QTableWidget`,
mismo criterio que `ProductTableModel` desde la fase 5.0. Es de solo
lectura: la edición pasa siempre por `CatalogProductEditorDialog`, no
por edición inline de celdas.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor

from cargo_optimizer.infrastructure.database.repositories import CatalogProductEntry
from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry

_color_registry = ColorRegistry()

COL_SKU = 0
COL_NAME = 1
COL_DIMENSIONS = 2
COL_WEIGHT = 3
COL_PACKAGE_TYPE = 4
COL_EXTINGUISHER = 5
COL_EXTINGUISHER_NOMINAL = 6
COL_MAX_STACK = 7
COL_ACTIVE = 8

_HEADERS = (
    "SKU",
    "Nombre",
    "Dimensiones (cm)",
    "Peso (kg)",
    "Tipo de empaque",
    "Extintor",
    "Peso nominal (kg)",
    "Apilamiento",
    "Activo",
)


class ProductCatalogTableModel(QAbstractTableModel):
    """Modelo de solo lectura sobre `tuple[CatalogProductEntry, ...]`."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[CatalogProductEntry] = []
        self._color_cache: dict[str, str] = {}

    def _rebuild_color_cache(self) -> None:
        sku_color_map = {e.load_unit.sku: e.load_unit.color_hex for e in self._entries}
        self._color_cache = _color_registry.assign_unique_palette_colors(sku_color_map)

    def set_entries(self, entries: Sequence[CatalogProductEntry]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self._rebuild_color_cache()
        self.endResetModel()

    def entry_at(self, row: int) -> CatalogProductEntry:
        return self._entries[row]

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(self._entries)

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

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        unit = entry.load_unit
        column = index.column()

        resolved = self._color_cache.get(unit.sku, "#CCCCCC")

        if role == Qt.ItemDataRole.DecorationRole and column == COL_SKU:
            return QColor(resolved)

        if role == Qt.ItemDataRole.BackgroundRole:
            color = QColor(resolved)
            color.setAlpha(35)
            return color

        if role == Qt.ItemDataRole.DisplayRole:
            if column == COL_SKU:
                return unit.sku
            if column == COL_NAME:
                return unit.name
            if column == COL_DIMENSIONS:
                dims = unit.dimensions
                return f"{dims.length_cm:g} x {dims.width_cm:g} x {dims.height_cm:g}"
            if column == COL_WEIGHT:
                return f"{unit.weight_kg:.1f}"
            if column == COL_PACKAGE_TYPE:
                return unit.package_type.value
            if column == COL_EXTINGUISHER:
                return "Sí" if unit.is_extinguisher else "No"
            if column == COL_EXTINGUISHER_NOMINAL:
                return (
                    f"{unit.extinguisher_nominal_kg:.1f}"
                    if unit.extinguisher_nominal_kg is not None
                    else ""
                )
            if column == COL_MAX_STACK:
                return str(unit.max_stack_count)
            if column == COL_ACTIVE:
                return "Sí" if entry.is_active else "No (archivado)"

        return None
