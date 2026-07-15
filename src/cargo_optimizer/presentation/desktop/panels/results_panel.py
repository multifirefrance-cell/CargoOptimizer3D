"""Panel inferior: resumen de resultados de la última optimización.

Desde la fase 5.1, `set_results` lo llama `MainWindow` al recibir un
`PackingResult` real de `OptimizationWorker`. El propio texto de
avisos vive en `WarningsPanel` (pestaña separada); aquí solo se
muestra el conteo, como resumen numérico.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

_EMPTY = "—"
_STALE_MESSAGE = "⚠ El resultado anterior fue invalidado porque el proyecto cambió."


class ResultsPanel(QWidget):
    """Resumen de la última ejecución del motor de optimización."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultsPanel")

        self._stale_label = QLabel(_STALE_MESSAGE, self)
        self._stale_label.setObjectName("resultsStaleLabel")
        self._stale_label.setWordWrap(True)
        self._stale_label.setVisible(False)

        self._requested_label = QLabel(_EMPTY, self)
        self._packed_label = QLabel(_EMPTY, self)
        self._pending_label = QLabel(_EMPTY, self)
        self._weight_label = QLabel(_EMPTY, self)
        self._volume_label = QLabel(_EMPTY, self)
        self._utilization_label = QLabel(_EMPTY, self)
        self._time_label = QLabel(_EMPTY, self)
        self._status_label = QLabel(_EMPTY, self)
        self._warnings_label = QLabel(_EMPTY, self)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Cantidad solicitada", self._requested_label)
        form.addRow("Cantidad cargada", self._packed_label)
        form.addRow("Cantidad pendiente", self._pending_label)
        form.addRow("Peso", self._weight_label)
        form.addRow("Volumen", self._volume_label)
        form.addRow("Utilización", self._utilization_label)
        form.addRow("Tiempo", self._time_label)
        form.addRow("Estado", self._status_label)
        form.addRow("Avisos", self._warnings_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(self._stale_label)
        layout.addLayout(form)

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
