"""`ProductTableModel`: tabla Qt de Load Units, respaldada por `QAbstractTableModel`.

Deliberadamente `QAbstractTableModel`, no `QTableWidget`: la tabla de
productos crecerá (edición por celda, ordenación, filtrado, y más
adelante import/export) y un modelo propio es la única forma de
soportar eso sin duplicar el estado en widgets. Cada fila es un
`cargo_optimizer.domain.load_unit.LoadUnit` real (frozen): editar una
celda reconstruye la instancia con `dataclasses.replace` y, si el
dominio la rechaza (`DomainValidationError`), la edición simplemente no
se aplica — nunca se deja el modelo en un estado inconsistente.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPersistentModelIndex, Qt
from PySide6.QtGui import QColor

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import LoadUnit

COL_SKU = 0
COL_NAME = 1
COL_QUANTITY = 2
COL_LENGTH = 3
COL_WIDTH = 4
COL_HEIGHT = 5
COL_WEIGHT = 6
COL_MAX_STACK = 7
COL_ORIENTATIONS = 8
COL_PACKAGE_TYPE = 9
COL_EXTINGUISHER = 10
COL_EXTINGUISHER_NOMINAL = 11
COL_FRAGILE = 12
COL_COLOR = 13

_HEADERS = (
    "SKU",
    "Nombre",
    "Cantidad",
    "Largo (cm)",
    "Ancho (cm)",
    "Alto (cm)",
    "Peso (kg)",
    "Apilamiento",
    "Orientaciones",
    "Tipo empaque",
    "Extintor",
    "Peso nominal (kg)",
    "Fragilidad",
    "Color",
)

_CHECKBOX_COLUMNS = frozenset({COL_EXTINGUISHER, COL_FRAGILE})
_TEXT_EDITABLE_COLUMNS = frozenset(
    {
        COL_SKU,
        COL_NAME,
        COL_QUANTITY,
        COL_LENGTH,
        COL_WIDTH,
        COL_HEIGHT,
        COL_WEIGHT,
        COL_MAX_STACK,
        COL_EXTINGUISHER_NOMINAL,
    }
)

_DEFAULT_EXTINGUISHER_NOMINAL_KG = 1.0


class ProductTableModel(QAbstractTableModel):
    """Modelo de tabla sobre una lista de `LoadUnit`."""

    def __init__(
        self, load_units: list[LoadUnit] | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._load_units: list[LoadUnit] = list(load_units) if load_units else []

    def load_units(self) -> tuple[LoadUnit, ...]:
        return tuple(self._load_units)

    def set_load_units(self, load_units: Sequence[LoadUnit]) -> None:
        """Reemplaza toda la tabla (apertura de un proyecto guardado)."""
        self.beginResetModel()
        self._load_units = list(load_units)
        self.endResetModel()

    def rowCount(  # noqa: N802
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()  # noqa: B008
    ) -> int:
        return 0 if parent.isValid() else len(self._load_units)

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
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        column = index.column()
        if column in _CHECKBOX_COLUMNS:
            return base | Qt.ItemFlag.ItemIsUserCheckable
        if column in _TEXT_EDITABLE_COLUMNS:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None
        unit = self._load_units[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and column in _CHECKBOX_COLUMNS:
            checked = unit.is_extinguisher if column == COL_EXTINGUISHER else unit.fragile
            return Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.DecorationRole and column == COL_COLOR:
            return QColor(unit.color_hex)

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self._display_value(unit, column)

        if role == Qt.ItemDataRole.TextAlignmentRole and column in (
            COL_QUANTITY,
            COL_LENGTH,
            COL_WIDTH,
            COL_HEIGHT,
            COL_WEIGHT,
            COL_MAX_STACK,
            COL_EXTINGUISHER_NOMINAL,
        ):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return None

    @staticmethod
    def _display_value(unit: LoadUnit, column: int) -> Any:
        if column == COL_SKU:
            return unit.sku
        if column == COL_NAME:
            return unit.name
        if column == COL_QUANTITY:
            return unit.quantity
        if column == COL_LENGTH:
            return unit.dimensions.length_cm
        if column == COL_WIDTH:
            return unit.dimensions.width_cm
        if column == COL_HEIGHT:
            return unit.dimensions.height_cm
        if column == COL_WEIGHT:
            return unit.weight_kg
        if column == COL_MAX_STACK:
            return unit.max_stack_count
        if column == COL_ORIENTATIONS:
            return str(len(unit.allowed_orientation_codes))
        if column == COL_PACKAGE_TYPE:
            return unit.package_type.value
        if column == COL_EXTINGUISHER_NOMINAL:
            return unit.extinguisher_nominal_kg if unit.extinguisher_nominal_kg is not None else ""
        if column == COL_COLOR:
            return unit.color_hex
        return None

    def setData(  # noqa: N802
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        column = index.column()
        unit = self._load_units[index.row()]

        try:
            if role == Qt.ItemDataRole.CheckStateRole and column in _CHECKBOX_COLUMNS:
                updated = self._with_checkbox(unit, column, value)
            elif role == Qt.ItemDataRole.EditRole and column in _TEXT_EDITABLE_COLUMNS:
                updated = self._with_text_value(unit, column, value)
            else:
                return False
        except (DomainValidationError, ValueError, TypeError):
            return False

        self._load_units[index.row()] = updated
        self.dataChanged.emit(index, index, [role])
        return True

    @staticmethod
    def _with_checkbox(unit: LoadUnit, column: int, value: Any) -> LoadUnit:
        checked = value == Qt.CheckState.Checked.value or value is True
        if column == COL_FRAGILE:
            return replace(unit, fragile=checked)
        # COL_EXTINGUISHER: mantener las invariantes de LoadUnit (agente y peso
        # nominal solo tienen sentido cuando is_extinguisher es True).
        if checked:
            agent = (
                unit.extinguisher_agent
                if unit.extinguisher_agent is not ExtinguisherAgent.NOT_APPLICABLE
                else ExtinguisherAgent.OTHER
            )
            nominal = unit.extinguisher_nominal_kg or _DEFAULT_EXTINGUISHER_NOMINAL_KG
            return replace(
                unit,
                is_extinguisher=True,
                extinguisher_agent=agent,
                extinguisher_nominal_kg=nominal,
            )
        return replace(
            unit,
            is_extinguisher=False,
            extinguisher_agent=ExtinguisherAgent.NOT_APPLICABLE,
            extinguisher_nominal_kg=None,
        )

    @staticmethod
    def _with_text_value(unit: LoadUnit, column: int, value: Any) -> LoadUnit:
        if column == COL_SKU:
            return replace(unit, sku=str(value))
        if column == COL_NAME:
            return replace(unit, name=str(value))
        if column == COL_QUANTITY:
            return replace(unit, quantity=int(value))
        if column == COL_WEIGHT:
            return replace(unit, weight_kg=float(value))
        if column == COL_MAX_STACK:
            return replace(unit, max_stack_count=int(value))
        if column == COL_EXTINGUISHER_NOMINAL:
            nominal = None if value in ("", None) else float(value)
            return replace(unit, extinguisher_nominal_kg=nominal)
        if column in (COL_LENGTH, COL_WIDTH, COL_HEIGHT):
            dims = unit.dimensions
            length, width, height = dims.length_cm, dims.width_cm, dims.height_cm
            if column == COL_LENGTH:
                length = float(value)
            elif column == COL_WIDTH:
                width = float(value)
            else:
                height = float(value)
            return replace(unit, dimensions=Dimensions3D(length, width, height))
        raise ValueError(f"Columna no editable como texto: {column}")

    def add_default_product(self) -> None:
        """Añade un `LoadUnit` de ejemplo neutro al final de la tabla (acción "Nuevo producto")."""
        index = len(self._load_units) + 1
        new_unit = LoadUnit(
            sku=f"SKU-{index:03d}",
            name="Nuevo producto",
            dimensions=Dimensions3D(40.0, 30.0, 20.0),
            weight_kg=10.0,
            package_type=PackageType.INDIVIDUAL,
        )
        row = len(self._load_units)
        self.beginInsertRows(QModelIndex(), row, row)
        self._load_units.append(new_unit)
        self.endInsertRows()

    def remove_rows_at(self, rows: list[int]) -> None:
        """Elimina las filas indicadas (índices de fila), en cualquier orden."""
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._load_units):
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._load_units[row]
                self.endRemoveRows()
