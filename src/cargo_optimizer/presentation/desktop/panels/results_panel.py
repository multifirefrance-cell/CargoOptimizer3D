"""Panel inferior: resumen de resultados de la última optimización.

Rediseño UX (auditoría "interfaz para usuarios, no para ingenieros"):
en vez de una lista `QFormLayout` de 9 filas con el mismo peso
tipográfico, los números clave (cargado/pendiente/%/volumen/peso/
tiempo) se muestran como tarjetas KPI grandes, con color de éxito o
advertencia según si quedaron unidades pendientes — para que el
usuario entienda el resultado de un vistazo, sin tener que leer cada
fila. Los nombres de los `QLabel` que ya usan las pruebas existentes
(`_requested_label`, `_packed_label`, `_pending_label`,
`_warnings_label`, `_stale_label`) se conservan sin cambios: solo
cambia cómo se presentan, nunca el contrato con `MainWindow.set_results`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.domain.unpacked_unit import UnpackedUnit
from cargo_optimizer.presentation.desktop.models.pending_sku_summary_model import (
    COL_NAME as _PSUMMARY_COL_NAME,
    COL_PACKED as _PSUMMARY_COL_PACKED,
    COL_PENDING as _PSUMMARY_COL_PENDING,
    COL_REQUESTED as _PSUMMARY_COL_REQUESTED,
    COL_SKU as _PSUMMARY_COL_SKU,
    PendingSkuSummaryModel,
)
from cargo_optimizer.presentation.desktop.style import (
    ERROR_DARK,
    ERROR_LIGHT,
    SPACING_SM,
    SPACING_XS,
    SUCCESS_DARK,
    SUCCESS_LIGHT,
    WARNING_DARK,
    WARNING_LIGHT,
    utilization_color,
)

_EMPTY = "—"
_STALE_MESSAGE = "⚠ El resultado anterior fue invalidado porque el proyecto cambió."

# Más compactas que en el diseño original (20pt/9pt): liberan altura para
# el visor 3D sin perder legibilidad (mejoras UX, corrección del bug de
# truncado — ver `_tile()`).
_VALUE_STYLE = "font-size: 15pt; font-weight: 700;"
_TITLE_STYLE = "font-size: 8pt; font-weight: 600; text-transform: uppercase;"


class _ClickableFrame(QFrame):
    """Un `QFrame` que emite `clicked` al pulsarlo (solo la tarjeta "Cantidad pendiente").

    `QFrame` no trae una señal de clic propia (a diferencia de
    `QPushButton`); en vez de rehacer la tarjeta como botón (perdería el
    estilo de tarjeta KPI del resto), se sobrescribe `mousePressEvent`
    para las pocas tarjetas que de verdad necesitan ser interactivas.
    """

    clicked = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


def _tile(title: str, *, clickable: bool = False) -> tuple[QFrame, QLabel]:
    """Una tarjeta KPI: título pequeño arriba, valor grande abajo. Devuelve `(tarjeta, valor)`.

    El título usa `setWordWrap(True)` en vez de dejar que se recorte: con
    seis tarjetas en una sola fila, un título largo ("Cantidad pendiente")
    no siempre cabe en una línea a un ancho de columna razonable — antes
    de esto, el texto que no cabía simplemente se recortaba (bug real de
    pérdida de información, no solo estético). `setMinimumWidth(0)` sobre
    la tarjeta permite que `QGridLayout` la encoja por debajo de su
    `sizeHint` cuando hace falta, en vez de forzar un ancho mínimo que
    reintroduciría el mismo problema en ventanas más estrechas.

    `clickable=True` (usado solo por "Cantidad pendiente") construye la
    tarjeta como `_ClickableFrame` en vez de `QFrame` liso, y añade un
    cursor de mano + tooltip -- para que abrir el detalle por SKU sea
    obvio, no un "easter egg" oculto (mejoras UX: el desglose por SKU ya
    existía pero no tenía ninguna vía visible de acceso).
    """
    frame = _ClickableFrame() if clickable else QFrame()
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    frame.setObjectName("kpiTile")
    frame.setMinimumWidth(0)
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    if clickable:
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setToolTip("Ver el detalle de unidades pendientes por SKU")
    title_label = QLabel(title, frame)
    title_label.setObjectName("kpiTileTitle")
    title_label.setStyleSheet(_TITLE_STYLE)
    title_label.setWordWrap(True)
    value_label = QLabel(_EMPTY, frame)
    value_label.setStyleSheet(_VALUE_STYLE)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
    layout.setSpacing(2)
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    return frame, value_label


class ResultsPanel(QWidget):
    """Resumen de la última ejecución del motor de optimización, como tarjetas KPI."""

    #: Se emite al pulsar la tarjeta "Cantidad pendiente" -- `MainWindow` la
    #: conecta para navegar a la pestaña "No cargados" (mejoras UX, no
    #: duplica el desglose por SKU, solo da una vía visible hacia él).
    pending_tile_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultsPanel")
        self._dark: bool = False
        self._last_pending: int | None = None
        self._last_status: str = ""
        self._last_util_pct: float = 0.0

        self._stale_label = QLabel(_STALE_MESSAGE, self)
        self._stale_label.setObjectName("resultsStaleLabel")
        self._stale_label.setWordWrap(True)
        self._stale_label.setStyleSheet(f"color: {WARNING_LIGHT.name()}; font-weight: 600;")
        self._stale_label.setVisible(False)

        self._packed_tile, self._packed_label = _tile("Cantidad cargada")
        self._packed_tile.setToolTip("Unidades que caben en el espacio de carga")
        self._pending_tile, self._pending_label = _tile("Cantidad pendiente", clickable=True)
        assert isinstance(self._pending_tile, _ClickableFrame)
        self._pending_tile.clicked.connect(self.pending_tile_clicked)
        self._utilization_tile, self._utilization_label = _tile("Utilización")
        self._utilization_tile.setToolTip("Porcentaje del volumen interior ocupado por las cajas")
        volume_tile, self._volume_label = _tile("Volumen")
        volume_tile.setToolTip("Volumen total ocupado por las cajas cargadas")
        weight_tile, self._weight_label = _tile("Peso")
        weight_tile.setToolTip("Peso total de las cajas cargadas")
        time_tile, self._time_label = _tile("Tiempo")
        time_tile.setToolTip("Tiempo de cálculo del motor de optimización")

        # Una sola fila de 6 tarjetas (antes 2x3): la disposición en dos
        # filas casi duplicaba la altura mínima de este panel. `setColumnStretch`
        # a 1 en las seis reparte el ancho disponible en partes iguales
        # (antes ninguna columna tenía stretch, así que cualquier ventana
        # que no fuera muy ancha dejaba a las tarjetas con menos ancho del
        # que su contenido necesitaba — la causa real del truncado de
        # títulos/unidades, no solo un problema estético).
        grid = QGridLayout()
        grid.setSpacing(SPACING_XS)
        for column, tile in enumerate(
            (self._utilization_tile, weight_tile, volume_tile, self._packed_tile, self._pending_tile, time_tile)
        ):
            grid.addWidget(tile, 0, column)
            grid.setColumnStretch(column, 1)

        self._requested_label = QLabel(_EMPTY, self)
        self._status_label = QLabel(_EMPTY, self)
        self._warnings_label = QLabel(_EMPTY, self)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(SPACING_SM)
        for caption, label in (
            ("Solicitado:", self._requested_label),
            ("Estado:", self._status_label),
            ("Avisos:", self._warnings_label),
        ):
            caption_label = QLabel(caption, self)
            caption_label.setStyleSheet("font-weight: 600;")
            detail_row.addWidget(caption_label)
            detail_row.addWidget(label)
            detail_row.addSpacing(SPACING_SM)
        detail_row.addStretch(1)

        # ── Tabla PENDIENTE POR SKU ──────────────────────────────────────────
        self.pending_summary_model = PendingSkuSummaryModel(self)
        self._sku_table = QTableView(self)
        self._sku_table.setObjectName("pendingSkuSummaryTableView")
        self._sku_table.setModel(self.pending_summary_model)
        self._sku_table.setAlternatingRowColors(False)
        self._sku_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._sku_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._sku_table.verticalHeader().setVisible(False)
        _sh = self._sku_table.horizontalHeader()
        _sh.setStretchLastSection(False)
        _sh.setSectionResizeMode(_PSUMMARY_COL_SKU, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(_PSUMMARY_COL_NAME, QHeaderView.ResizeMode.Stretch)
        _sh.setSectionResizeMode(_PSUMMARY_COL_REQUESTED, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(_PSUMMARY_COL_PACKED, QHeaderView.ResizeMode.Interactive)
        _sh.setSectionResizeMode(_PSUMMARY_COL_PENDING, QHeaderView.ResizeMode.Interactive)
        _sh.resizeSection(_PSUMMARY_COL_SKU, 90)
        _sh.resizeSection(_PSUMMARY_COL_REQUESTED, 95)
        _sh.resizeSection(_PSUMMARY_COL_PACKED, 95)
        _sh.resizeSection(_PSUMMARY_COL_PENDING, 95)

        sku_section_label = QLabel("PENDIENTE POR SKU", self)
        sku_section_label.setProperty("class", "sectionLabel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_XS)
        layout.addWidget(self._stale_label)
        layout.addLayout(grid)
        layout.addLayout(detail_row)
        layout.addSpacing(SPACING_XS)
        layout.addWidget(sku_section_label)
        layout.addWidget(self._sku_table, 1)

    def clear(self) -> None:
        self._last_pending = None
        self._last_status = ""
        self._last_util_pct = 0.0
        for label in (
            self._requested_label,
            self._packed_label,
            self._pending_label,
            self._weight_label,
            self._volume_label,
            self._utilization_label,
            self._time_label,
            self._status_label,
            self._warnings_label,
        ):
            label.setText(_EMPTY)
        self._packed_label.setStyleSheet(_VALUE_STYLE)
        self._pending_label.setStyleSheet(_VALUE_STYLE)
        self._utilization_label.setStyleSheet(_VALUE_STYLE)
        for tile in (self._packed_tile, self._pending_tile, self._utilization_tile):
            self._clear_tile_accent(tile)
        self.set_stale(False)
        self.pending_summary_model.clear()

    def set_result(
        self,
        placements: Sequence[Placement],
        unpacked_units: Sequence[UnpackedUnit],
        load_units_by_id: Mapping[UUID, LoadUnit],
    ) -> None:
        """Actualiza la tabla PENDIENTE POR SKU con el último resultado."""
        self.pending_summary_model.set_result(placements, unpacked_units, load_units_by_id)

    def _set_tile_accent(self, tile: QFrame, hex_color: str) -> None:
        if self._dark:
            bg, hover_bg = "#23272E", "#2A2F38"
            border, hover_border = "#343840", "#4A4F5A"
        else:
            bg, hover_bg = "#F5F7FA", "#EDF0F5"
            border, hover_border = "#E0E3E8", "#C0C4CC"
        tile.setStyleSheet(
            f"QFrame#kpiTile {{ background: {bg}; border: 1px solid {border}; "
            f"border-left: 3px solid {hex_color}; border-radius: 6px; }}"
            f"QFrame#kpiTile:hover {{ background: {hover_bg}; border: 1px solid {hover_border}; "
            f"border-left: 3px solid {hex_color}; }}"
        )

    @staticmethod
    def _clear_tile_accent(tile: QFrame) -> None:
        tile.setStyleSheet("")

    def _refresh_accent_colors(self) -> None:
        if self._last_pending is None:
            return
        if self._last_pending == 0 and self._last_status != "Cancelado":
            emphasis_color = SUCCESS_DARK if self._dark else SUCCESS_LIGHT
        elif self._last_status == "Cancelado":
            emphasis_color = ERROR_DARK if self._dark else ERROR_LIGHT
        else:
            emphasis_color = WARNING_DARK if self._dark else WARNING_LIGHT
        emphasis_hex = emphasis_color.name()
        emphasis_style = f"{_VALUE_STYLE} color: {emphasis_hex};"
        self._packed_label.setStyleSheet(emphasis_style)
        self._pending_label.setStyleSheet(emphasis_style)
        self._set_tile_accent(self._packed_tile, emphasis_hex)
        self._set_tile_accent(self._pending_tile, emphasis_hex)
        util_color = utilization_color(self._last_util_pct)
        self._utilization_label.setStyleSheet(f"{_VALUE_STYLE} color: {util_color};")
        self._set_tile_accent(self._utilization_tile, util_color)

    def set_dark_mode(self, dark: bool) -> None:
        self._dark = dark
        warning = WARNING_DARK if dark else WARNING_LIGHT
        self._stale_label.setStyleSheet(f"color: {warning.name()}; font-weight: 600;")
        self._refresh_accent_colors()

    def set_stale(self, stale: bool) -> None:
        """Muestra u oculta el aviso de "resultado invalidado" (fase 7.0)."""
        self._stale_label.setVisible(stale)

    def set_results(
        self,
        *,
        requested_count: int,
        packed_count: int,
        pending_count: int,
        weight_kg: float,
        volume_m3: float,
        utilization_percent: float,
        elapsed_seconds: float,
        status: str,
        warnings_count: int,
    ) -> None:
        self._requested_label.setText(str(requested_count))
        self._packed_label.setText(str(packed_count))
        self._pending_label.setText(str(pending_count))
        self._weight_label.setText(f"{weight_kg:.1f} kg")
        self._volume_label.setText(f"{volume_m3:.3f} m³")
        self._utilization_label.setText(f"{utilization_percent:.1f} %")
        self._time_label.setText(f"{elapsed_seconds:.2f} s")
        self._status_label.setText(status)
        self._warnings_label.setText("Ninguno" if warnings_count == 0 else str(warnings_count))

        self._last_pending = pending_count
        self._last_status = status
        self._last_util_pct = utilization_percent
        self._refresh_accent_colors()
