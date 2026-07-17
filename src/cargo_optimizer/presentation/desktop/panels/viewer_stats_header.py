"""Barra encima del visor 3D: nombre del espacio de carga + dimensiones + volumen/peso/utilización.

Rediseño UX ("workspace operativo"): el encargo original pedía que,
encima del visor 3D, se mostrara el espacio de carga elegido (nombre +
dimensiones) junto con el volumen/peso/utilización del último
resultado, sin tener que cambiar a la pestaña "Resumen" para verlo
mientras se mira la escena. No sustituye a `ResultsPanel` (que sigue
siendo la fuente completa de KPIs, incluida la comparación
cargado/pendiente): esta barra es un resumen mínimo de una sola línea.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from cargo_optimizer.domain.loading_space import LoadingSpace

_EMPTY = "—"


def _stat_text(label: str, value: float | None, unit: str) -> str:
    if value is None:
        return f"{label}: {_EMPTY}"
    if unit == "%":
        return f"{label}: {value:.1f} %"
    if unit == "m3":
        return f"{label}: {value:.2f} m³"
    return f"{label}: {value:,.0f} kg".replace(",", ".")


class ViewerStatsHeader(QWidget):
    """Nombre + dimensiones del espacio, y volumen/peso/utilización del último resultado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("viewerStatsHeader")

        self._name_label = QLabel(_EMPTY, self)
        self._name_label.setStyleSheet("font-weight: 700; font-size: 11pt;")
        self._dimensions_label = QLabel(_EMPTY, self)
        self._volume_label = QLabel(_stat_text("Volumen", None, "m3"), self)
        self._weight_label = QLabel(_stat_text("Peso", None, "kg"), self)
        self._utilization_label = QLabel(_stat_text("Utilización", None, "%"), self)

        layout = QHBoxLayout(self)
        layout.addWidget(self._name_label)
        layout.addWidget(self._dimensions_label)
        layout.addStretch(1)
        layout.addWidget(self._volume_label)
        layout.addWidget(self._weight_label)
        layout.addWidget(self._utilization_label)

    def set_space(self, space: LoadingSpace | None) -> None:
        if space is None:
            self._name_label.setText(_EMPTY)
            self._dimensions_label.setText(_EMPTY)
            return
        self._name_label.setText(space.name)
        dims = space.internal_dimensions
        self._dimensions_label.setText(
            f"{dims.length_cm:.0f} × {dims.width_cm:.0f} × {dims.height_cm:.0f} cm"
        )

    def set_result_stats(
        self, *, volume_m3: float, weight_kg: float, utilization_percent: float
    ) -> None:
        self._volume_label.setText(_stat_text("Volumen", volume_m3, "m3"))
        self._weight_label.setText(_stat_text("Peso", weight_kg, "kg"))
        self._utilization_label.setText(_stat_text("Utilización", utilization_percent, "%"))

    def clear_result_stats(self) -> None:
        self._volume_label.setText(_stat_text("Volumen", None, "m3"))
        self._weight_label.setText(_stat_text("Peso", None, "kg"))
        self._utilization_label.setText(_stat_text("Utilización", None, "%"))
