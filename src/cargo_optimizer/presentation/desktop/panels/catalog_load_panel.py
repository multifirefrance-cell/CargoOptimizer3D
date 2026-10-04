"""Panel izquierdo de carga: tabla del catálogo con cantidad y color editables.

Reemplaza el buscador puntual de `ProductQuickAddPanel`. Muestra todos los
SKUs activos del catálogo en una tabla de edición directa:

  [color] | SKU | Nombre | Cantidad

- El color por SKU se persiste en el catálogo (se guarda al cambiar).
- El usuario escribe la cantidad que quiere cargar en la columna "Cant.".
- "Agregar a la carga" añade al modelo de carga todos los SKUs con Cant > 0
  y resetea las cantidades a 0.
- "+ Catálogo INDUPROX" abre el selector de SKUs predefinidos para agregar
  nuevos productos al catálogo.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import PackageType
from cargo_optimizer.domain.load_unit import DEFAULT_MAX_STACK_COUNT, LoadUnit
from cargo_optimizer.infrastructure.database.exceptions import RepositoryError
from cargo_optimizer.infrastructure.database.repositories import ProductCatalogRepository
from cargo_optimizer.presentation.desktop.dialogs.induprox_sku_picker_dialog import (
    _SKUS as _INDUPROX_SKUS,
    _SkuDef,
)

# Campos editables por el usuario que se leen desde la DB (sobreescriben el valor
# del catálogo hardcodeado). Los campos algorítmicos (orientaciones, flags de
# extintor, gap_fill) siguen siendo los de _INDUPROX_SKUS para garantizar que el
# motor de optimización funciona correctamente con independencia del editor.
_DB_OVERRIDABLE = frozenset({"dimensions", "weight_kg", "name", "color_hex"})

def _sku_def_to_load_unit(sd: _SkuDef, color_hex: str) -> LoadUnit:
    return LoadUnit(
        id=uuid4(),
        sku=sd.sku,
        name=sd.name,
        dimensions=Dimensions3D(sd.length_cm, sd.width_cm, sd.height_cm),
        weight_kg=sd.weight_kg,
        package_type=PackageType.INDIVIDUAL,
        units_per_package=1,
        max_stack_count=30 if sd.is_extinguisher else DEFAULT_MAX_STACK_COUNT,
        max_supported_weight_kg=None,
        allowed_orientation_codes=sd.orientation_codes,
        gap_fill_orientation_codes=sd.gap_fill_codes,
        fragile=False,
        is_extinguisher=sd.is_extinguisher,
        extinguisher_agent=sd.extinguisher_agent,
        extinguisher_nominal_kg=sd.extinguisher_nominal_kg,
        color_hex=color_hex,
        notes="",
    )


class _SpinBox(QSpinBox):
    """QSpinBox que muestra '—' para cero sin usar setSpecialValueText.

    setSpecialValueText bloquea el teclado porque el validador de enteros
    rechaza cualquier dígito añadido a "—". Esta implementación muestra "—"
    via textFromValue/valueFromText/validate, lo que deja el validador limpio
    para tipeo normal. Al ganar foco selecciona todo para que el primer dígito
    reemplace el "—" visible.
    """

    def textFromValue(self, value: int) -> str:
        return "—" if value == 0 else super().textFromValue(value)

    def valueFromText(self, text: str) -> int:
        return 0 if text.strip() in ("—", "") else super().valueFromText(text)

    def validate(self, text: str, pos: int):
        if text.strip() in ("—", ""):
            return (QValidator.State.Acceptable, text, pos)
        return super().validate(text, pos)

    def keyPressEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.KeypadModifier:
            from PySide6.QtGui import QKeyEvent
            remapped = QKeyEvent(
                event.type(),
                event.key(),
                Qt.KeyboardModifier.NoModifier,
                event.text(),
            )
            super().keyPressEvent(remapped)
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        QTimer.singleShot(0, self.lineEdit().selectAll)


_PALETTE: tuple[str, ...] = (
    "#E53935", "#E91E63", "#AB47BC", "#5C6BC0",
    "#1E88E5", "#26C6DA", "#26A69A", "#66BB6A",
    "#9CCC65", "#FFCA28", "#FFA726", "#FF7043",
    "#8D6E63", "#78909C", "#BDBDBD", "#42A5F5",
)


def seed_induprox_catalog(repository: ProductCatalogRepository) -> int:
    """Sincroniza el catálogo con los SKUs INDUPROX definidos en código.

    - Archiva los productos activos que NO estén en `_INDUPROX_SKUS`.
    - Agrega los SKUs INDUPROX que aún no estén presentes.
    Devuelve el número total de cambios (archivados + nuevos insertados).
    """
    induprox_skus_lower = {sd.sku.lower() for sd in _INDUPROX_SKUS}
    active_units = repository.list_active()
    archived = 0
    for unit in active_units:
        if unit.sku.lower() not in induprox_skus_lower:
            try:
                repository.archive(unit.id)
                archived += 1
            except Exception:
                pass

    existing = {u.sku.lower() for u in repository.list_active()}
    used_colors = {u.color_hex.lower() for u in repository.list_active()}
    color_idx = 0
    added = 0
    for sd in _INDUPROX_SKUS:
        if sd.sku.lower() in existing:
            continue
        while color_idx < len(_PALETTE) and _PALETTE[color_idx].lower() in used_colors:
            color_idx += 1
        color = _PALETTE[color_idx % len(_PALETTE)]
        used_colors.add(color.lower())
        color_idx += 1
        unit = _sku_def_to_load_unit(sd, color)
        try:
            repository.add(unit)
            added += 1
        except Exception:
            pass
    return archived + added


class _ColorPickerPopup(QDialog):
    """Popup de paleta de 16 colores; se cierra al hacer clic en un color."""

    def __init__(
        self, current: str, used: tuple[str, ...], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._chosen = current
        used_set = {c.lower() for c in used}
        grid = QGridLayout(self)
        grid.setSpacing(4)
        grid.setContentsMargins(6, 6, 6, 6)
        for i, color in enumerate(_PALETTE):
            btn = QPushButton(self)
            btn.setFixedSize(26, 26)
            selected = color.lower() == current.lower()
            in_use = color.lower() in used_set
            if selected:
                border = "3px solid #1a1a1a"
            elif in_use:
                border = "2px solid #FB8C00"
            else:
                border = "2px solid rgba(0,0,0,0.15)"
            btn.setStyleSheet(
                f"QPushButton {{ background:{color}; border:{border}; border-radius:4px; }}"
                f"QPushButton:hover {{ border:2px solid #444; }}"
            )
            btn.setToolTip(color + (" · ya en uso" if in_use else ""))
            btn.clicked.connect(lambda *, c=color: self._pick(c))
            grid.addWidget(btn, i // 8, i % 8)

    def _pick(self, color: str) -> None:
        self._chosen = color
        self.accept()

    def chosen_color(self) -> str:
        return self._chosen


class CatalogLoadPanel(QWidget):
    """Tabla editable del catálogo: color · SKU · Nombre · Cantidad."""

    #: (LoadUnit del catálogo, cantidad) — emitido por cada SKU con qty > 0
    add_requested = Signal(object, int)

    def __init__(
        self, parent: QWidget | None = None, *, repository: ProductCatalogRepository | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("catalogLoadPanel")
        self._repository = repository
        self._units: list[LoadUnit] = []
        self._color_buttons: list[QPushButton] = []
        self._qty_spins: list[QSpinBox] = []

        # ── Botón principal ─────────────────────────────────────────────
        self._add_button = QPushButton("Agregar a la carga", self)
        self._add_button.setProperty("class", "primary")
        self._add_button.setMinimumHeight(34)
        self._add_button.clicked.connect(self._on_add_clicked)

        # ── Tabla de catálogo ────────────────────────────────────────────
        self._table = QTableWidget(0, 4, self)
        self._table.setObjectName("catalogLoadTable")
        self._table.setHorizontalHeaderLabels(["", "SKU", "Nombre", "QTY"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setDefaultSectionSize(28)
        _h = self._table.horizontalHeader()
        _h.setStretchLastSection(False)
        _h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        _h.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        _h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        _h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 34)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(3, 105)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.setMinimumHeight(80)  # permite que el splitter encoja el panel si falta espacio

        # ── Layout ───────────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(4, 4, 4, 4)
        top_row.setSpacing(6)
        top_row.addWidget(self._add_button, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top_row)
        layout.addWidget(self._table, 1)

        self._reload()

    # ── API pública ───────────────────────────────────────────────────────

    def set_repository(self, repository: ProductCatalogRepository | None) -> None:
        self._repository = repository
        self._reload()

    def refresh_catalog(self) -> None:
        self._reload()

    # ── Carga interna ─────────────────────────────────────────────────────

    def _reload(self) -> None:
        self._units.clear()
        self._color_buttons.clear()
        self._qty_spins.clear()
        self._table.setRowCount(0)

        # Leer todos los datos editables desde la DB (dimensiones, peso, nombre, color).
        db_units: dict[str, LoadUnit] = {}
        if self._repository is not None:
            for unit in self._repository.list_active():
                db_units[unit.sku] = unit

        # Asignar colores del palette a SKUs que no tienen uno guardado en DB.
        used_colors: set[str] = {u.color_hex.lower() for u in db_units.values()}
        color_map: dict[str, str] = {sku: u.color_hex for sku, u in db_units.items()}
        for i, sd in enumerate(_INDUPROX_SKUS):
            if sd.sku not in color_map:
                color = next(
                    (c for c in _PALETTE if c.lower() not in used_colors),
                    _PALETTE[i % len(_PALETTE)],
                )
                used_colors.add(color.lower())
                color_map[sd.sku] = color

        # Mostrar todos los SKUs del catálogo INDUPROX en orden del catálogo.
        # Dimensiones y peso: desde DB si el usuario los editó; hardcodeado si no.
        for sd in _INDUPROX_SKUS:
            unit = _sku_def_to_load_unit(sd, color_map[sd.sku])
            if sd.sku in db_units:
                db = db_units[sd.sku]
                unit = replace(unit, dimensions=db.dimensions, weight_kg=db.weight_kg, name=db.name)
            self._append_row(unit)

    def _append_row(self, unit: LoadUnit) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._units.append(unit)

        # ── Color swatch ──────────────────────────────────────────────
        color_btn = QPushButton()
        color_btn.setFixedSize(22, 22)
        color_btn.setToolTip("Cambiar color en el visor 3D")
        self._apply_swatch_style(color_btn, unit.color_hex)
        color_btn.clicked.connect(lambda *, r=row: self._on_color_click(r))
        self._color_buttons.append(color_btn)

        swatch_container = QWidget()
        swatch_layout = QHBoxLayout(swatch_container)
        swatch_layout.setContentsMargins(5, 3, 3, 3)
        swatch_layout.addWidget(color_btn)
        self._table.setCellWidget(row, 0, swatch_container)

        # ── SKU ───────────────────────────────────────────────────────
        sku_item = QTableWidgetItem(unit.sku)
        sku_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row, 1, sku_item)

        # ── Nombre ────────────────────────────────────────────────────
        name_item = QTableWidgetItem(unit.name)
        name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row, 2, name_item)

        # ── Cantidad (SpinBox embebido) ───────────────────────────────
        spin = _SpinBox()
        spin.setRange(0, 99999999)
        spin.setValue(0)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qty_spins.append(spin)
        self._table.setCellWidget(row, 3, spin)

    @staticmethod
    def _apply_swatch_style(btn: QPushButton, hex_color: str) -> None:
        btn.setStyleSheet(
            f"QPushButton {{ background:{hex_color}; border:1px solid rgba(0,0,0,0.2); border-radius:3px; }}"
            f"QPushButton:hover {{ border:2px solid #333; }}"
        )

    # ── Handlers ──────────────────────────────────────────────────────────

    def _on_color_click(self, row: int) -> None:
        if row >= len(self._units):
            return
        unit = self._units[row]
        used = tuple(u.color_hex for i, u in enumerate(self._units) if i != row)
        popup = _ColorPickerPopup(unit.color_hex, used, self)
        btn = self._color_buttons[row]
        global_pos = btn.mapToGlobal(btn.rect().bottomLeft())
        popup.move(global_pos)
        popup.exec()
        new_color = popup.chosen_color()
        if new_color.lower() == unit.color_hex.lower():
            return
        updated = replace(unit, color_hex=new_color)
        self._units[row] = updated
        self._apply_swatch_style(self._color_buttons[row], new_color)
        # Persistir color en repositorio (buscar por SKU o crear si no existe).
        if self._repository is not None:
            try:
                existing_by_sku = {u.sku: u for u in self._repository.list_active()}
                if unit.sku in existing_by_sku:
                    self._repository.update(replace(existing_by_sku[unit.sku], color_hex=new_color))
                else:
                    self._repository.add(replace(updated, id=uuid4()))
            except RepositoryError as exc:
                QMessageBox.warning(self, "Error al guardar color", str(exc))

    def _on_add_clicked(self) -> None:
        for unit, spin in zip(self._units, self._qty_spins):
            qty = spin.value()
            if qty > 0:
                self.add_requested.emit(unit, qty)
                spin.setValue(0)

