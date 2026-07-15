"""`LoadingSpaceProfileTableModel`: tabla de solo lectura sobre perfiles de espacio (fase 7.1)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt

from cargo_optimizer.infrastructure.database.repositories import LoadingSpaceProfileEntry

COL_NAME = 0
COL_CATEGORY = 1
COL_DIMENSIONS = 2
COL_MAX_WEIGHT = 3
COL_DOOR_POSITION = 4
COL_ORIGIN = 5

_HEADERS = ("Nombre", "Categoría", "Dimensiones (cm)", "Peso máximo (kg)", "Puerta", "Origen")


class LoadingSpaceProfileTableModel(QAbstractTableModel):
    """Modelo de solo lectura sobre `tuple[LoadingSpaceProfileEntry, ...]`."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[LoadingSpaceProfileEntry] = []

    def set_entries(self, entries: Sequence[LoadingSpaceProfileEntry]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def entry_at(self, row: int) -> LoadingSpaceProfileEntry:
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
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        entry = self._entries[index.row()]
        space = entry.loading_space
        column = index.column()

        if column == COL_NAME:
            return space.name
        if column == COL_CATEGORY:
            return space.category.value
        if column == COL_DIMENSIONS:
            dims = space.internal_dimensions
            return f"{dims.length_cm:g} x {dims.width_cm:g} x {dims.height_cm:g}"
        if column == COL_MAX_WEIGHT:
            return f"{space.max_weight_kg:.1f}" if space.max_weight_kg is not None else "Sin límite"
        if column == COL_DOOR_POSITION:
            return space.door_position.value
        if column == COL_ORIGIN:
            if not entry.is_active:
                return "Archivado"
            return "Integrado" if entry.is_builtin else "Personalizado"
        return None
