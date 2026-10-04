"""Barra encima del visor 3D: nombre/dimensiones del espacio + KPIs + botones de vista.

Rediseño UX ("workspace operativo"): el encargo original pedía que,
encima del visor 3D, se mostrara el espacio de carga elegido (nombre +
dimensiones) junto con el volumen/peso/utilización del último
resultado, sin tener que cambiar a la pestaña "Resumen" para verlo
mientras se mira la escena.

Esta versión añade:
- Barra de progreso de utilización (visual, al estilo EasyCargo), en vez
  de solo texto
- Botones de vista (Iso / Frontal / Superior / Lateral) directamente en
  la barra, sin tener que ir al menú Ver
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.style import utilization_color

_EMPTY = "—"


class ViewerStatsHeader(QWidget):
    """Nombre + dimensiones del espacio, barra de utilización, KPIs y accesos rápidos de vista."""

    # Señales para que MainWindow conecte con las acciones de cámara existentes
    reset_camera_requested = Signal()
    view_front_requested = Signal()
    view_top_requested = Signal()
    view_side_requested = Signal()
    sku_visibility_changed = Signal(str, bool)  # (sku, visible)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("viewerStatsHeader")
        self.setAutoFillBackground(True)
        self._dark = False

        # --- Nombre + dimensiones ---
        self._name_label = QLabel(_EMPTY, self)
        self._name_label.setStyleSheet("font-weight: 700; font-size: 10.5pt;")
        self._dimensions_label = QLabel(_EMPTY, self)
        self._dimensions_label.setStyleSheet("color: #888; font-size: 9pt;")

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name_col.addWidget(self._name_label)
        name_col.addWidget(self._dimensions_label)

        # --- Barra de utilización ---
        self._utilization_value_label = QLabel(_EMPTY, self)
        self._utilization_value_label.setStyleSheet("font-weight: 700; font-size: 10pt;")
        self._utilization_value_label.setMinimumWidth(50)
        self._utilization_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._utilization_bar = QProgressBar(self)
        self._utilization_bar.setObjectName("utilizationBar")
        self._utilization_bar.setRange(0, 100)
        self._utilization_bar.setValue(0)
        self._utilization_bar.setTextVisible(False)
        self._utilization_bar.setFixedHeight(8)
        self._utilization_bar.setMinimumWidth(120)
        self._utilization_bar.setMaximumWidth(200)
        self._utilization_bar.setStyleSheet(self._bar_stylesheet(0.0))

        util_caption = QLabel("Utilización", self)
        util_caption.setStyleSheet("font-size: 8pt; color: #888;")

        util_col = QVBoxLayout()
        util_col.setSpacing(2)
        util_col.addWidget(util_caption)
        util_col.addWidget(self._utilization_bar)

        util_row = QHBoxLayout()
        util_row.setSpacing(6)
        util_row.addLayout(util_col)
        util_row.addWidget(self._utilization_value_label)

        # --- Peso y volumen ---
        self._weight_label = QLabel(_EMPTY, self)
        self._weight_label.setStyleSheet("font-size: 9pt;")
        self._volume_label = QLabel(_EMPTY, self)
        self._volume_label.setStyleSheet("font-size: 9pt;")

        kpi_col = QVBoxLayout()
        kpi_col.setSpacing(1)
        kpi_col.addWidget(self._weight_label)
        kpi_col.addWidget(self._volume_label)

        # --- Botones de vista ---
        self._btn_iso = self._view_button("⟐ Iso")
        self._btn_iso.setToolTip("Vista isométrica  (Ctrl+0)")
        self._btn_front = self._view_button("◫ Frente")
        self._btn_front.setToolTip("Vista frontal  (Ctrl+1)")
        self._btn_top = self._view_button("⬜ Superior")
        self._btn_top.setToolTip("Vista superior  (Ctrl+2)")
        self._btn_side = self._view_button("▭ Lateral")
        self._btn_side.setToolTip("Vista lateral  (Ctrl+3)")

        self._btn_iso.clicked.connect(self.reset_camera_requested)
        self._btn_front.clicked.connect(self.view_front_requested)
        self._btn_top.clicked.connect(self.view_top_requested)
        self._btn_side.clicked.connect(self.view_side_requested)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.addWidget(self._btn_iso)
        btn_row.addWidget(self._btn_front)
        btn_row.addWidget(self._btn_top)
        btn_row.addWidget(self._btn_side)

        # --- Leyenda de colores SKU (segunda fila, oculta hasta primer resultado) ---
        self._legend_row = QWidget(self)
        self._legend_row.setObjectName("skuLegendRow")
        self._legend_row.setVisible(False)
        self._legend_row_layout = QHBoxLayout(self._legend_row)
        self._legend_row_layout.setContentsMargins(0, 2, 0, 0)
        self._legend_row_layout.setSpacing(14)

        # --- Layout principal ---
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(20)
        top_row.addLayout(name_col)
        top_row.addLayout(util_row)
        top_row.addLayout(kpi_col)
        top_row.addStretch(1)
        top_row.addLayout(btn_row)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 4)
        main_layout.setSpacing(2)
        main_layout.addLayout(top_row)
        main_layout.addWidget(self._legend_row)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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
        pct = max(0.0, min(100.0, utilization_percent))
        self._utilization_bar.setValue(int(round(pct)))
        self._utilization_bar.setStyleSheet(self._bar_stylesheet(pct, dark=self._dark))
        self._utilization_value_label.setText(f"{pct:.1f} %")
        color = utilization_color(pct)
        self._utilization_value_label.setStyleSheet(
            f"font-weight: 700; font-size: 10pt; color: {color};"
        )
        self._weight_label.setText(f"Peso: {weight_kg:,.0f} kg".replace(",", "."))
        self._volume_label.setText(f"Volumen: {volume_m3:.2f} m³")

    def clear_result_stats(self) -> None:
        self._utilization_bar.setValue(0)
        self._utilization_bar.setStyleSheet(self._bar_stylesheet(0.0, dark=self._dark))
        self._utilization_value_label.setText(_EMPTY)
        self._utilization_value_label.setStyleSheet("font-weight: 700; font-size: 10pt;")
        self._weight_label.setText(_EMPTY)
        self._volume_label.setText(_EMPTY)
        self._clear_legend()

    def set_sku_legend(self, color_by_sku: dict[str, str]) -> None:
        """Muestra checkboxes de filtro por SKU con swatch de color debajo de la barra principal."""
        self._clear_legend()
        if not color_by_sku:
            return
        for sku, color_hex in sorted(color_by_sku.items()):
            # Usar QWidget contenedor (no sub-layout) para que _clear_legend
            # pueda destruirlo con deleteLater() — item.widget() es None para
            # sub-layouts y los chips viejos quedarían superpuestos al redibujar.
            chip = QWidget(self._legend_row)
            chip_layout = QHBoxLayout(chip)
            chip_layout.setSpacing(4)
            chip_layout.setContentsMargins(0, 0, 0, 0)

            swatch = QLabel(chip)
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(
                f"background: {color_hex}; border-radius: 2px; border: 1px solid rgba(0,0,0,0.15);"
            )
            cb = QCheckBox(sku, chip)
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 8pt;")
            cb.checkStateChanged.connect(
                lambda state, s=sku: self.sku_visibility_changed.emit(
                    s, state == Qt.CheckState.Checked
                )
            )
            chip_layout.addWidget(swatch)
            chip_layout.addWidget(cb)
            self._legend_row_layout.addWidget(chip)
        self._legend_row_layout.addStretch(1)
        self._legend_row.setVisible(True)

    def _clear_legend(self) -> None:
        while self._legend_row_layout.count():
            item = self._legend_row_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
        self._legend_row.setVisible(False)

    def set_dark_mode(self, dark: bool) -> None:
        self._dark = dark
        dim_color = "#AAAAAA" if dark else "#888"
        self._dimensions_label.setStyleSheet(f"color: {dim_color}; font-size: 9pt;")
        current_pct = float(self._utilization_bar.value())
        self._utilization_bar.setStyleSheet(self._bar_stylesheet(current_pct, dark=dark))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _view_button(self, text: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    @staticmethod
    def _bar_stylesheet(pct: float, *, dark: bool = False) -> str:
        if pct >= 85:
            fill = "#43A047"
        elif pct >= 60:
            fill = "#FB8C00"
        elif pct > 0:
            fill = "#1E88E5"
        else:
            fill = "#B0B5BC"  # gris — sin resultado aún
        track = "#2A2D33" if dark else "#E0E3E8"
        return f"""
            QProgressBar {{
                background: {track};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {fill};
                border-radius: 4px;
            }}
        """
