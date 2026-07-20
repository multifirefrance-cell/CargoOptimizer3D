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

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.presentation.desktop.style import (
    ERROR_LIGHT,
    SPACING_SM,
    SPACING_XS,
    SUCCESS_LIGHT,
    WARNING_LIGHT,
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

        self._stale_label = QLabel(_STALE_MESSAGE, self)
        self._stale_label.setObjectName("resultsStaleLabel")
        self._stale_label.setWordWrap(True)
        self._stale_label.setStyleSheet(f"color: {WARNING_LIGHT.name()}; font-weight: 600;")
        self._stale_label.setVisible(False)

        packed_tile, self._packed_label = _tile("Cantidad cargada")
        pending_tile, self._pending_label = _tile("Cantidad pendiente", clickable=True)
        assert isinstance(pending_tile, _ClickableFrame)
        pending_tile.clicked.connect(self.pending_tile_clicked)
        utilization_tile, self._utilization_label = _tile("Utilización")
        volume_tile, self._volume_label = _tile("Volumen")
        weight_tile, self._weight_label = _tile("Peso")
        time_tile, self._time_label = _tile("Tiempo")

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
            (utilization_tile, weight_tile, volume_tile, packed_tile, pending_tile, time_tile)
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_XS)
        layout.addWidget(self._stale_label)
        layout.addLayout(grid)
        layout.addLayout(detail_row)
        layout.addStretch(1)

    def clear(self) -> None:
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
        self.set_stale(False)

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

        # Color de estado: verde cuando todo se cargó, ámbar cuando quedaron
        # unidades pendientes, rojo si además la ejecución se canceló — el
        # usuario entiende el resultado sin leer cada tarjeta (rediseño UX).
        if pending_count == 0 and status != "Cancelado":
            emphasis_color = SUCCESS_LIGHT
        elif status == "Cancelado":
            emphasis_color = ERROR_LIGHT
        else:
            emphasis_color = WARNING_LIGHT
        emphasis_style = f"{_VALUE_STYLE} color: {emphasis_color.name()};"
        self._packed_label.setStyleSheet(emphasis_style)
        self._pending_label.setStyleSheet(emphasis_style)
        self._utilization_label.setStyleSheet(emphasis_style)
