"""Panel de resultados de una asignación automática multi-espacio (OPT-01, UI).

Muestra el resumen global de `MultiSpaceAssignmentResult` (todo
calculado, nunca duplicado — ver `docs/MultiSpaceAssignment.md`) y, vía
un selector simple ("Espacio 1"..."Espacio N"), el resumen, avisos y
unidades no cargadas de un `PackingResult` individual. El panel no
toca el visor 3D directamente: emite `space_selected(int)` para que
`MainWindow` decida cómo actualizarlo, mismo desacoplo que ya usa
`viewer_widget.placement_selected` con `_on_placement_selected`.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.application.codes import MultiSpaceStopReason
from cargo_optimizer.application.models import MultiSpaceAssignmentResult
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.presentation.desktop.style import utilization_color
from cargo_optimizer.presentation.desktop.models.unpacked_table_model import (
    COL_CODE as UNPACKED_COL_CODE,
    COL_INSTANCE as UNPACKED_COL_INSTANCE,
    COL_REASON as UNPACKED_COL_REASON,
    COL_SKU as UNPACKED_COL_SKU,
    UnpackedUnitTableModel,
)

_EMPTY = "—"
_NO_WARNINGS_MESSAGE = "Sin avisos."

_WARNING_BG = QColor("#FFF8E1")
_WARNING_FG = QColor("#7A4F00")
_WARNING_BG_DARK = QColor("#2A2010")
_WARNING_FG_DARK = QColor("#F2A93B")


def _apply_utilization_color(label: QLabel, text: str) -> None:
    """Sets label text and colors it by the percentage value contained in the text."""
    label.setText(text)
    try:
        pct = float(text.split("%")[0].strip())
        label.setStyleSheet(f"color: {utilization_color(pct)}; font-weight: 600;")
    except (ValueError, IndexError):
        label.setStyleSheet("")

_STOP_REASON_LABELS: dict[MultiSpaceStopReason, str] = {
    MultiSpaceStopReason.ALL_PACKED: "Toda la carga se ubicó",
    MultiSpaceStopReason.IMPOSSIBLE_REMAINING: "Carga restante imposible con los candidatos dados",
    MultiSpaceStopReason.MAX_SPACES_REACHED: "Se alcanzó el máximo de espacios permitido",
    MultiSpaceStopReason.CANCELLED: "Cancelado por el usuario",
}


class MultiSpaceResultsPanel(QWidget):
    """Resumen global + selector de espacio individual de una asignación multi-espacio."""

    space_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("multiSpaceResultsPanel")
        self._result: MultiSpaceAssignmentResult | None = None
        self._load_units_by_id: Mapping[UUID, LoadUnit] = {}
        self._dark: bool = False

        self._global_group = QGroupBox("Resumen global", self)
        self._spaces_used_label = QLabel(_EMPTY, self)
        self._spaces_by_name_label = QLabel(_EMPTY, self)
        self._spaces_by_name_label.setWordWrap(True)
        self._requested_label = QLabel(_EMPTY, self)
        self._packed_label = QLabel(_EMPTY, self)
        self._pending_label = QLabel(_EMPTY, self)
        self._capacity_volume_label = QLabel(_EMPTY, self)
        self._used_volume_label = QLabel(_EMPTY, self)
        self._volume_utilization_label = QLabel(_EMPTY, self)
        self._weight_label = QLabel(_EMPTY, self)
        self._min_utilization_label = QLabel(_EMPTY, self)
        self._avg_utilization_label = QLabel(_EMPTY, self)
        self._max_utilization_label = QLabel(_EMPTY, self)
        self._stop_reason_label = QLabel(_EMPTY, self)
        self._total_time_label = QLabel(_EMPTY, self)

        global_form = QFormLayout(self._global_group)
        global_form.addRow("Espacios utilizados", self._spaces_used_label)
        global_form.addRow("Cantidad por tipo/nombre", self._spaces_by_name_label)
        global_form.addRow("Unidades solicitadas", self._requested_label)
        global_form.addRow("Unidades cargadas", self._packed_label)
        global_form.addRow("Unidades pendientes", self._pending_label)
        global_form.addRow("Volumen disponible", self._capacity_volume_label)
        global_form.addRow("Volumen utilizado", self._used_volume_label)
        global_form.addRow("Ocupación global", self._volume_utilization_label)
        global_form.addRow("Peso cargado", self._weight_label)
        global_form.addRow("Ocupación mínima", self._min_utilization_label)
        global_form.addRow("Ocupación media", self._avg_utilization_label)
        global_form.addRow("Ocupación máxima", self._max_utilization_label)
        global_form.addRow("Razón de parada", self._stop_reason_label)
        global_form.addRow("Tiempo total", self._total_time_label)

        self._space_combo = QComboBox(self)
        self._space_combo.setObjectName("multiSpaceSelectorCombo")
        self._space_combo.currentIndexChanged.connect(self._on_space_index_changed)

        self._individual_group = QGroupBox("Espacio seleccionado", self)
        self._individual_packed_label = QLabel(_EMPTY, self)
        self._individual_volume_label = QLabel(_EMPTY, self)
        self._individual_weight_label = QLabel(_EMPTY, self)
        individual_form = QFormLayout(self._individual_group)
        individual_form.addRow("Cargado / solicitado", self._individual_packed_label)
        individual_form.addRow("Utilización de volumen", self._individual_volume_label)
        individual_form.addRow("Peso cargado", self._individual_weight_label)

        self._warnings_list = QListWidget(self)
        self._warnings_list.setObjectName("multiSpaceWarningsList")

        self._unpacked_model = UnpackedUnitTableModel(self)
        self._unpacked_table = QTableView(self)
        self._unpacked_table.setObjectName("multiSpaceUnpackedTableView")
        self._unpacked_table.setModel(self._unpacked_model)
        self._unpacked_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._unpacked_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._unpacked_table.verticalHeader().setVisible(False)
        _uh = self._unpacked_table.horizontalHeader()
        _uh.setStretchLastSection(False)
        _uh.setSectionResizeMode(UNPACKED_COL_SKU, QHeaderView.ResizeMode.Interactive)
        _uh.setSectionResizeMode(UNPACKED_COL_INSTANCE, QHeaderView.ResizeMode.Interactive)
        _uh.setSectionResizeMode(UNPACKED_COL_REASON, QHeaderView.ResizeMode.Stretch)
        _uh.setSectionResizeMode(UNPACKED_COL_CODE, QHeaderView.ResizeMode.Interactive)
        _uh.resizeSection(UNPACKED_COL_SKU, 90)
        _uh.resizeSection(UNPACKED_COL_INSTANCE, 75)
        _uh.resizeSection(UNPACKED_COL_CODE, 100)

        # Este panel apila un formulario de 14 filas + selector + otro
        # formulario + una lista + una tabla: sin envolverlo en un
        # `QScrollArea`, su `minimumSizeHint()` (varios cientos de px)
        # pasaba a ser el mínimo de **todo** `results_tabs`
        # (`QTabWidget.minimumSizeHint()` es el máximo entre todas sus
        # pestañas, aunque solo "Multi-espacio" lo necesite) — forzando a
        # reservar ese espacio incluso viendo la pestaña "Resumen", que
        # apenas necesita ~95px. Con el contenido dentro de un scroll, el
        # mínimo del panel vuelve a ser trivial y el contenido solo
        # aparece recortado con barra de desplazamiento cuando de verdad
        # falta espacio, nunca forzando el resto de la ventana.
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(self._global_group)
        content_layout.addWidget(QLabel("Espacio:", content))
        content_layout.addWidget(self._space_combo)
        content_layout.addWidget(self._individual_group)
        content_layout.addWidget(QLabel("Avisos del espacio seleccionado", content))
        content_layout.addWidget(self._warnings_list)
        content_layout.addWidget(QLabel("No cargados del espacio seleccionado", content))
        content_layout.addWidget(self._unpacked_table)

        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("multiSpaceResultsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        self.clear()

    def set_dark_mode(self, dark: bool) -> None:
        self._dark = dark
        if self._result is not None:
            current = self._space_combo.currentIndex()
            if current >= 0:
                self._display_space(current)

    def clear(self) -> None:
        self._result = None
        self._load_units_by_id = {}
        styled_labels = (
            self._packed_label,
            self._pending_label,
            self._volume_utilization_label,
            self._min_utilization_label,
            self._avg_utilization_label,
            self._max_utilization_label,
            self._individual_volume_label,
            self._individual_packed_label,
        )
        for label in (
            self._spaces_used_label,
            self._spaces_by_name_label,
            self._requested_label,
            self._packed_label,
            self._pending_label,
            self._capacity_volume_label,
            self._used_volume_label,
            self._volume_utilization_label,
            self._weight_label,
            self._min_utilization_label,
            self._avg_utilization_label,
            self._max_utilization_label,
            self._stop_reason_label,
            self._total_time_label,
            self._individual_packed_label,
            self._individual_volume_label,
            self._individual_weight_label,
        ):
            label.setText(_EMPTY)
        for label in styled_labels:
            label.setStyleSheet("")
        self._space_combo.blockSignals(True)
        self._space_combo.clear()
        self._space_combo.blockSignals(False)
        self._warnings_list.clear()
        self._unpacked_model.set_unpacked_units((), {})

    def set_result(
        self, result: MultiSpaceAssignmentResult, load_units_by_id: Mapping[UUID, LoadUnit]
    ) -> None:
        self._result = result
        self._load_units_by_id = load_units_by_id

        self._spaces_used_label.setText(str(result.spaces_used_count))
        by_name = ", ".join(
            f"{name}: {count}" for name, count in result.spaces_used_by_candidate_name.items()
        )
        self._spaces_by_name_label.setText(by_name or _EMPTY)
        self._requested_label.setText(str(result.total_requested_count))
        packed = result.total_packed_count
        pending = result.pending_count
        if pending == 0:
            packed_color = "#43A047"
            pending_color = "#43A047"
        else:
            packed_color = "#FB8C00"
            pending_color = "#C62828"
        self._packed_label.setText(str(packed))
        self._packed_label.setStyleSheet(f"color: {packed_color}; font-weight: 600;")
        self._pending_label.setText(str(pending))
        self._pending_label.setStyleSheet(f"color: {pending_color}; font-weight: 600;")
        self._capacity_volume_label.setText(
            f"{result.total_capacity_volume_cm3 / 1_000_000.0:.3f} m³"
        )
        self._used_volume_label.setText(f"{result.total_used_volume_cm3 / 1_000_000.0:.3f} m³")
        _apply_utilization_color(
            self._volume_utilization_label,
            f"{result.overall_volume_utilization_percent:.1f} %",
        )
        self._weight_label.setText(f"{result.total_used_weight_kg:.1f} kg")
        _apply_utilization_color(
            self._min_utilization_label,
            f"{result.min_volume_utilization_percent:.1f} %",
        )
        _apply_utilization_color(
            self._avg_utilization_label,
            f"{result.average_volume_utilization_percent:.1f} %",
        )
        _apply_utilization_color(
            self._max_utilization_label,
            f"{result.max_volume_utilization_percent:.1f} %",
        )
        self._stop_reason_label.setText(
            _STOP_REASON_LABELS.get(result.stop_reason, result.stop_reason.value)
        )
        self._total_time_label.setText(f"{result.execution_time_seconds:.2f} s")

        self._space_combo.blockSignals(True)
        self._space_combo.clear()
        for index, sr in enumerate(result.space_results):
            space_name = getattr(getattr(sr, "loading_space", None), "name", None)
            label = f"{index + 1}. {space_name}" if space_name else f"Espacio {index + 1}"
            self._space_combo.addItem(label)
        self._space_combo.blockSignals(False)
        if result.space_results:
            self._space_combo.setCurrentIndex(0)
            self._display_space(0)

    def _on_space_index_changed(self, index: int) -> None:
        if index < 0:
            return
        self._display_space(index)
        self.space_selected.emit(index)

    def _display_space(self, index: int) -> None:
        if self._result is None or not (0 <= index < len(self._result.space_results)):
            return
        space_result = self._result.space_results[index]
        packed_text = f"{space_result.packed_count} / {space_result.requested_count}"
        self._individual_packed_label.setText(packed_text)
        if space_result.packed_count >= space_result.requested_count:
            self._individual_packed_label.setStyleSheet("color: #43A047; font-weight: 600;")
        elif space_result.packed_count > 0:
            self._individual_packed_label.setStyleSheet("color: #FB8C00; font-weight: 600;")
        else:
            self._individual_packed_label.setStyleSheet("color: #C62828; font-weight: 600;")
        _apply_utilization_color(
            self._individual_volume_label,
            f"{space_result.volume_utilization_percent:.1f} %",
        )
        self._individual_weight_label.setText(f"{space_result.used_weight_kg:.1f} kg")

        self._warnings_list.clear()
        if not space_result.warnings:
            placeholder = QListWidgetItem(_NO_WARNINGS_MESSAGE)
            self._warnings_list.addItem(placeholder)
        else:
            for warning in space_result.warnings:
                item = QListWidgetItem(f"⚠  {warning}")
                item.setBackground(_WARNING_BG)
                item.setForeground(_WARNING_FG)
                self._warnings_list.addItem(item)

        self._unpacked_model.set_unpacked_units(space_result.unpacked_units, self._load_units_by_id)

    def current_space_index(self) -> int:
        return self._space_combo.currentIndex()
