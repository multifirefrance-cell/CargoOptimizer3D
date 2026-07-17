"""Panel compacto: elegir un producto del catálogo (o crear uno nuevo) y agregarlo con cantidad.

Rediseño UX ("workspace operativo"): la operación diaria más frecuente
—agregar un producto ya existente en el catálogo a la carga actual con
una cantidad— usa un combo desplegable editable en vez de un campo de
texto con autocompletado a ciegas: la flecha del combo muestra de
inmediato **toda** la lista de productos activos del catálogo, sin que
el usuario tenga que escribir nada para descubrir qué existe; si
escribe, el propio combo filtra la lista igual que antes. El editor
completo (`CatalogProductEditorDialog`) solo se abre para "Crear nuevo
SKU…", cuando el producto todavía no existe en el catálogo.

Reutiliza `ProductCatalogRepository.search`/`get_by_sku`/`list_active`
(ya existente, usado también por `ProductCatalogDialog`) para resolver
el producto elegido/tecleado — nunca reimplementa la búsqueda ni
duplica productos: este panel solo *resuelve* un `LoadUnit` de catálogo
y una cantidad; quien lo use decide cómo copiarlo al proyecto
(`CatalogService.copy_to_project`, igual que el flujo "Añadir desde
catálogo…" ya existente).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.dialogs.catalog_product_editor_dialog import (
    CatalogProductEditorDialog,
)

_EMPTY_INFO = ""
_NOT_AVAILABLE_MESSAGE = "Catálogo no disponible en esta sesión."


def _display_text(unit: LoadUnit) -> str:
    return f"{unit.sku} — {unit.name}"


class ProductQuickAddPanel(QWidget):
    """Combo de catálogo (lista completa o escribir para filtrar) + cantidad + "Agregar"."""

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

        self._search_combo = QComboBox(self)
        self._search_combo.setObjectName("productSearchCombo")
        self._search_combo.setEditable(True)
        self._search_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # El propio `QComboBox` instala un `QCompleter` sobre su modelo al
        # ser editable: se ajusta para que filtre por coincidencia en
        # cualquier parte del texto (no solo al inicio) — la flecha del
        # combo ya muestra la lista completa sin necesidad de escribir
        # nada, esto solo mejora el filtrado mientras se escribe.
        combo_completer = self._search_combo.completer()
        if combo_completer is not None:
            combo_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            combo_completer.setFilterMode(Qt.MatchFlag.MatchContains)

        self._create_sku_button = QPushButton("Crear nuevo SKU…", self)
        self._create_sku_button.setFlat(True)

        self._quantity_spin = QSpinBox(self)
        self._quantity_spin.setRange(1, 999_999)
        self._quantity_spin.setValue(1)

        self._add_button = QPushButton("+ AGREGAR A LA CARGA", self)
        self._add_button.setEnabled(False)

        self._info_label = QLabel(_EMPTY_INFO, self)
        self._info_label.setWordWrap(True)

        self._search_combo.editTextChanged.connect(self._on_search_text_changed)
        self._create_sku_button.clicked.connect(self._on_create_new_sku)
        self._add_button.clicked.connect(self._on_add_clicked)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("SKU o Nombre", self))
        search_row.addWidget(self._search_combo, 1)
        search_row.addWidget(self._create_sku_button)

        quantity_row = QHBoxLayout()
        quantity_row.addWidget(QLabel("Cantidad", self))
        quantity_row.addWidget(self._quantity_spin)
        quantity_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel("<b>AGREGAR PRODUCTOS A LA CARGA</b>", self))
        layout.addLayout(search_row)
        layout.addWidget(self._info_label)
        layout.addLayout(quantity_row)
        layout.addWidget(self._add_button)

        self.set_repository(repository)

    def set_repository(self, repository: ProductCatalogRepository | None) -> None:
        """Cambia (o quita) el repositorio de catálogo — modo limitado si es `None`."""
        self._repository = repository
        available = repository is not None
        self._search_combo.setEnabled(available)
        self._create_sku_button.setEnabled(available)
        line_edit = self._search_combo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText("SKU o nombre…" if available else _NOT_AVAILABLE_MESSAGE)
        self.refresh_catalog()

    def refresh_catalog(self) -> None:
        """Recarga la lista completa de productos activos del catálogo en el combo."""
        self._by_sku.clear()
        self._by_display_text.clear()
        if self._repository is not None:
            for unit in self._repository.list_active():
                self._by_sku[unit.sku.lower()] = unit
                self._by_display_text[_display_text(unit)] = unit
        current_text = self._search_combo.currentText()
        self._search_combo.blockSignals(True)
        self._search_combo.clear()
        self._search_combo.addItems(sorted(self._by_display_text.keys()))
        self._search_combo.setCurrentText(current_text)
        self._search_combo.blockSignals(False)
        self._resolve_current_text()

    def _on_search_text_changed(self, _text: str) -> None:
        self._resolve_current_text()

    def _resolve_current_text(self) -> None:
        text = self._search_combo.currentText().strip()
        unit = self._by_display_text.get(text) or self._by_sku.get(text.lower())
        self._resolved_unit = unit
        if unit is None:
            self._info_label.setText(_EMPTY_INFO)
            self._add_button.setEnabled(False)
            return
        dims = unit.dimensions
        self._info_label.setText(
            f"{unit.sku} — {unit.name} — "
            f"{dims.length_cm:.0f} × {dims.width_cm:.0f} × {dims.height_cm:.0f} cm — "
            f"{unit.weight_kg:.1f} kg"
        )
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
        dialog = CatalogProductEditorDialog(self, title="Nuevo producto")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        unit = dialog.result_load_unit()
        if unit is None:
            return
        try:
            self._repository.add(unit)
        except RepositoryError as exc:
            QMessageBox.warning(self, "No se pudo crear el producto", str(exc))
            return
        self.refresh_catalog()
        self._search_combo.setCurrentText(_display_text(unit))
