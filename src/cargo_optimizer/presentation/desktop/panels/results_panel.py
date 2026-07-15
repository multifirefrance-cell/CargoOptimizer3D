"""Panel inferior: resumen de resultados de la última optimización.

Fase 5.0: valores siempre vacíos (`—`), porque `PackingEngine` no se
invoca todavía desde la interfaz. `set_results` ya existe con la forma
final que usará la fase 5.1 (cantidades, peso, volumen, utilización,
tiempo, estado) para no tener que rediseñar el panel al conectar el
motor, pero nada la llama todavía.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

_EMPTY = "—"


class ResultsPanel(QWidget):
    """Resumen de la última ejecución del motor de optimización."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultsPanel")

        self._requested_label = QLabel(_EMPTY, self)
        self._packed_label = QLabel(_EMPTY, self)
        self._weight_label = QLabel(_EMPTY, self)
        self._volume_label = QLabel(_EMPTY, self)
        self._utilization_label = QLabel(_EMPTY, self)
        self._time_label = QLabel(_EMPTY, self)
        self._status_label = QLabel(_EMPTY, self)

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addRow("Cantidad solicitada", self._requested_label)
        layout.addRow("Cantidad cargada", self._packed_label)
        layout.addRow("Peso", self._weight_label)
        layout.addRow("Volumen", self._volume_label)
        layout.addRow("Utilización", self._utilization_label)
        layout.addRow("Tiempo", self._time_label)
        layout.addRow("Estado", self._status_label)

    def clear(self) -> None:
        for label in (
            self._requested_label,
            self._packed_label,
            self._weight_label,
            self._volume_label,
            self._utilization_label,
            self._time_label,
            self._status_label,
        ):
            label.setText(_EMPTY)

    def set_results(
        self,
        *,
        requested_count: int,
        packed_count: int,
        weight_kg: float,
        volume_m3: float,
        utilization_percent: float,
        elapsed_seconds: float,
        status: str,
    ) -> None:
        """Forma final del panel para la fase 5.1 — no invocada todavía en esta fase."""
        self._requested_label.setText(str(requested_count))
        self._packed_label.setText(str(packed_count))
        self._weight_label.setText(f"{weight_kg:.1f} kg")
        self._volume_label.setText(f"{volume_m3:.3f} m³")
        self._utilization_label.setText(f"{utilization_percent:.1f} %")
        self._time_label.setText(f"{elapsed_seconds:.2f} s")
        self._status_label.setText(status)
