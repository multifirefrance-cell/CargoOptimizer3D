"""Panel para agregar un producto del catálogo a la carga.

Flujo:
  1. Abrir el combo (flecha) o escribir para buscar por SKU o nombre.
  2. Al seleccionar aparece una tarjeta con color, SKU, nombre y dimensiones.
  3. Ajustar cantidad y pulsar "Agregar a la carga" (botón rojo).

"Crear nuevo SKU…" abre el editor completo solo cuando el producto no existe.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.dialogs.induprox_sku_picker_dialog import (
    InduproxSkuPickerDialog,
)
from cargo_optimizer.presentation.desktop.style import SPACING_SM, SPACING_XS
from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry

_color_registry = ColorRegistry()

_NOT_AVAILABLE_MESSAGE = "Catálogo no disponible."


def _display_text(unit: LoadUnit) -> str:
    return f"{unit.sku}  —  {unit.name}"


class _ProductCard(QFrame):
    """Tarjeta compacta con color, SKU, nombre y dimensiones del producto seleccionado."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("productCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._swatch = QLabel(self)
        self._swatch.setFixedSize(28, 44)
        self._swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._sku_label = QLabel(self)
        self._sku_label.setStyleSheet("font-weight: 700; font-size: 8.5pt; color: palette(mid);")

        self._name_label = QLabel(self)
        self._name_label.setStyleSheet("font-weight: 600; font-size: 10pt;")

        self._dims_label = QLabel(self)
        self._dims_label.setStyleSheet("font-size: 8.5pt; color: palette(mid);")

        info = QVBoxLayout()
        info.setSpacing(1)
        info.setContentsMargins(0, 0, 0, 0)
        info.addWidget(self._sku_label)
        info.addWidget(self._name_label)
        info.addWidget(self._dims_label)

        row = QHBoxLayout(self)
        row.setContentsMargins(SPACING_XS, SPACING_XS, SPACING_SM, SPACING_XS)
        row.setSpacing(SPACING_SM)
        row.addWidget(self._swatch)
        row.addLayout(info, 1)

    def set_unit(self, unit: LoadUnit, resolved_color: str | None = None) -> None:
        color = resolved_color or _color_registry.resolve_color(unit.color_hex, fallback_key=unit.sku)
        self._swatch.setStyleSheet(
            f"background: {color}; border-radius: 3px; border: 1px solid rgba(0,0,0,0.12);"
        )
        # Banda izquierda de color — incluimos el resto del estilo explícitamente para
        # no perder los colores de fondo/borde del QSS global al sobreescribir
        self.setStyleSheet(
            f"QFrame#productCard {{"
            f"  background: palette(base);"
            f"  border: 1px solid palette(mid);"
            f"  border-left: 4px solid {color};"
            f"  border-radius: 6px;"
            f"}}"
        )
        self._sku_label.setText(unit.sku)
        name = unit.name if len(unit.name) <= 35 else unit.name[:33] + "…"
        self._name_label.setText(name)
        d = unit.dimensions
        self._dims_label.setText(
            f"{d.length_cm:.0f} × {d.width_cm:.0f} × {d.height_cm:.0f} cm  ·  {unit.weight_kg:.1f} kg"
        )


class ProductQuickAddPanel(QWidget):
    """Búsqueda de catálogo + tarjeta de producto + cantidad + botón Agregar."""

    add_requested = Signal(object, int)  # (LoadUnit del catálogo, cantidad)

    def __init__(
        self, parent: QWidget | None = None, *, repository: ProductCatalogRepository | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("productQuickAddPanel")
        self._repository = repository
        self._by_sku: dict[str, LoadUnit] = {}
        self._by_display_text: dict[str, LoadUnit] = {}
        self._resolved_unit: LoadUnit | None = None
        self._color_by_sku: dict[str, str] = {}

        # ── Combo de búsqueda ──────────────────────────────────────────
        self._search_combo = QComboBox(self)
        self._search_combo.setObjectName("productSearchCombo")
        self._search_combo.setEditable(True)
        self._search_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._search_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search_combo.setMinimumHeight(34)
        combo_completer = self._search_combo.completer()
        if combo_completer is not None:
            combo_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            combo_completer.setFilterMode(Qt.MatchFlag.MatchContains)

        # ── Tarjeta del producto seleccionado ─────────────────────────
        self._product_card = _ProductCard(self)
        self._product_card.setVisible(False)

        # ── Cantidad + botón Agregar ───────────────────────────────────
        qty_label = QLabel("Cantidad:", self)
        qty_label.setStyleSheet("font-weight: 600;")

        self._quantity_spin = QSpinBox(self)
        self._quantity_spin.setRange(1, 999_999)
        self._quantity_spin.setValue(1)
        self._quantity_spin.setMinimumWidth(75)
        self._quantity_spin.setMinimumHeight(34)

        self._add_button = QPushButton("Agregar a la carga", self)
        self._add_button.setObjectName("addToLoadButton")
        self._add_button.setProperty("class", "primary")
        self._add_button.setEnabled(False)
        self._add_button.setMinimumHeight(34)
        self._add_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        qty_row = QHBoxLayout()
        qty_row.setSpacing(SPACING_SM)
        qty_row.addWidget(qty_label)
        qty_row.addWidget(self._quantity_spin)
        qty_row.addWidget(self._add_button, 1)

        # ── Botón catálogo INDUPROX ────────────────────────────────────
        self._create_sku_button = QPushButton("+ Catálogo INDUPROX", self)
        self._create_sku_button.setProperty("class", "compact")
        self._create_sku_button.setToolTip("Agregar un SKU del catálogo de productos INDUPROX")

        # ── Señales ───────────────────────────────────────────────────
        self._search_combo.editTextChanged.connect(self._on_search_text_changed)
        self._create_sku_button.clicked.connect(self._on_create_new_sku)
        self._add_button.clicked.connect(self._on_add_clicked)

        # ── Layout principal ──────────────────────────────────────────
        section_label = QLabel("AGREGAR A LA CARGA", self)
        section_label.setStyleSheet(
            "font-weight: 700; font-size: 9pt; color: #999; letter-spacing: 0.5px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, SPACING_XS)
        layout.setSpacing(SPACING_SM)
        layout.addWidget(section_label)
        layout.addWidget(self._search_combo)
        layout.addWidget(self._product_card)
        layout.addLayout(qty_row)
        layout.addWidget(self._create_sku_button)

        self.set_repository(repository)

    # ── API pública ────────────────────────────────────────────────────

    def set_repository(self, repository: ProductCatalogRepository | None) -> None:
        """Cambia (o quita) el repositorio de catálogo."""
        self._repository = repository
        available = repository is not None
        self._search_combo.setEnabled(available)
        self._create_sku_button.setEnabled(available)
        line_edit = self._search_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(
                "Buscar por SKU o nombre…" if available else _NOT_AVAILABLE_MESSAGE
            )
        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        """Recarga la lista completa de productos activos en el combo."""
        self._by_sku.clear()
        self._by_display_text.clear()
        all_units: list = []
        if self._repository is not None:
            for unit in self._repository.list_active():
                self._by_sku[unit.sku.lower()] = unit
                self._by_display_text[_display_text(unit)] = unit
                all_units.append(unit)

        # Asignar colores únicos sin colisiones para todos los SKUs juntos
        sku_color_map = {u.sku: u.color_hex for u in all_units}
        self._color_by_sku = _color_registry.assign_unique_palette_colors(sku_color_map)
        color_by_sku = self._color_by_sku

        current_text = self._search_combo.currentText()
        self._search_combo.blockSignals(True)
        self._search_combo.clear()
        sorted_texts = sorted(self._by_display_text.keys())
        self._search_combo.addItems(sorted_texts)
        for i, display_text in enumerate(sorted_texts):
            unit = self._by_display_text[display_text]
            color = color_by_sku.get(unit.sku, "#CCCCCC")
            self._search_combo.setItemData(i, QColor(color), Qt.ItemDataRole.DecorationRole)
        self._search_combo.setCurrentText(current_text)
        self._search_combo.blockSignals(False)
        self._resolve_current_text()

    # ── Implementación interna ─────────────────────────────────────────

    def _on_search_text_changed(self, _text: str) -> None:
        self._resolve_current_text()

    def _resolve_current_text(self) -> None:
        text = self._search_combo.currentText().strip()
        unit = self._by_display_text.get(text) or self._by_sku.get(text.lower())
        self._resolved_unit = unit
        if unit is None:
            self._product_card.setVisible(False)
            self._add_button.setEnabled(False)
        else:
            resolved_color = self._color_by_sku.get(unit.sku)
            self._product_card.set_unit(unit, resolved_color)
            self._product_card.setVisible(True)
            self._add_button.setEnabled(True)

    def _on_add_clicked(self) -> None:
        if self._resolved_unit is None:
            return
        quantity = self._quantity_spin.value()
        if quantity < 1:
            return
        self.add_requested.emit(self._resolved_unit, quantity)
        self._search_combo.setCurrentText("")
        self._quantity_spin.setValue(1)

    def _on_create_new_sku(self) -> None:
        if self._repository is None:
            return
        existing_colors = tuple(unit.color_hex for unit in self._repository.list_active())
        existing_skus = frozenset(unit.sku for unit in self._repository.list_active())
        dialog = InduproxSkuPickerDialog(
            self, existing_colors=existing_colors, existing_skus=existing_skus
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        unit = dialog.result_load_unit()
        if unit is None:
            return
        try:
            self._repository.add(unit)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo agregar el SKU", str(exc))
            return
        self.refresh_catalog()
        self._search_combo.setCurrentText(_display_text(unit))
