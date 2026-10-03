"""Diálogo de selección de SKU del catálogo INDUPROX para importar a CargoOptimizer3D.

Muestra los 45 SKUs predefinidos con dimensiones estándar de caja.
El usuario filtra por categoría, selecciona un SKU, elige el color
y confirma. El diálogo devuelve un `LoadUnit` listo para agregar al
catálogo local del proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.enums import OrientationCode
from cargo_optimizer.domain.load_unit import DEFAULT_MAX_STACK_COUNT, DEFAULT_ORIENTATION_CODES, LoadUnit

# Extintores portátiles: acostados (H = eje largo del cilindro).
# Ronda 1: HWL_XYZ → H a lo largo de X (puerta→fondo); llena el bloque principal.
# Ronda 2: WHL_XYZ → H a lo largo de Y (90° transversal); rellena el hueco X sobrante.
# Solo se necesita una orientación por ronda: todos los SKUs de extintor tienen l=w
# (sección circular), así que HLW≡HWL y LHW≡WHL.
_EXT_ORIENTATIONS: tuple[OrientationCode, ...] = (
    OrientationCode.HWL_XYZ,   # H→X  (principal)
    OrientationCode.WHL_XYZ,   # H→Y  (relleno 90° transversal)
)
# Ronda 3 (relleno "de pie"): LWH_XYZ → H vertical (Z); para aprovechar
# los huecos residuales donde el extintor acostado ya no cabe pero sí cabe de pie.
# Se aplica SOLO en espacios sobrantes tras las rondas 1 y 2.
_EXT_GAP_FILL: tuple[OrientationCode, ...] = (
    OrientationCode.LWH_XYZ,   # L→X, W→Y, H→Z  (de pie)
)

_CAT_ALL = "Todos"
_CAT_EXTINTORES = "Extintores"
_CAT_CARROS = "Carros extintor"
_CAT_GABINETES = "Gabinetes / Carretes"
_CAT_SOPORTES = "Soportes"
_CAT_FUNDAS = "Fundas / Mantas"
_CAT_MANGUERAS = "Mangueras / Válvulas"
_CAT_ACCESORIOS = "Accesorios"

CATEGORIES = (
    _CAT_ALL,
    _CAT_EXTINTORES,
    _CAT_CARROS,
    _CAT_GABINETES,
    _CAT_SOPORTES,
    _CAT_FUNDAS,
    _CAT_MANGUERAS,
    _CAT_ACCESORIOS,
)


@dataclass(frozen=True)
class _SkuDef:
    sku: str
    name: str
    length_cm: float
    width_cm: float
    height_cm: float
    weight_kg: float
    category: str
    is_extinguisher: bool = False
    extinguisher_agent: ExtinguisherAgent = ExtinguisherAgent.NOT_APPLICABLE
    extinguisher_nominal_kg: float | None = None
    orientation_codes: tuple[OrientationCode, ...] = DEFAULT_ORIENTATION_CODES
    gap_fill_codes: tuple[OrientationCode, ...] = ()


# Dimensiones de caja según estándar internacional para cada tipo de producto.
# Fuente: normas EN 3 (extintores portátiles), IRAM 3517/3518, datos de catálogos
# EXANCO/GETPRO y estimaciones de embalaje estándar para accesorios contra incendios.
_SKUS: tuple[_SkuDef, ...] = (
    _SkuDef("35.781",  "EXTINTOR PQS ABC 4KG 90%",                  14, 14, 50, 6.5,  _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 4.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("35.782",  "EXTINTOR PQS ABC 6KG 90% EXANCO",           17, 17, 60, 9.5,  _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 6.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("35.783",  "EXTINTOR PQS ABC 10KG 90% EXANCO",          21, 21, 72, 14.5, _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 10.0, _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("95.803",  "EXTINTOR PQS ABC 1KG 90%",                  10, 10, 36, 2.5,  _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 1.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("120.842", "GABINETE EXT POLICARBONATO 6KG",             42, 22, 62, 4.0,  _CAT_GABINETES),
    _SkuDef("120.843", "GABINETE EXT POLICARBONATO 10KG",            50, 26, 74, 5.5,  _CAT_GABINETES),
    _SkuDef("121.068", "EXTINTOR CO2 2KG EXANCO",                    14, 14, 52, 9.0,  _CAT_EXTINTORES, True, ExtinguisherAgent.CO2, 2.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("135.475", "EXTINTOR CO2 5KG",                           18, 18, 70, 20.0, _CAT_EXTINTORES, True, ExtinguisherAgent.CO2, 5.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("136.096", "SOPORTE EXTINTOR 6 KG AUTO",                 26,  8, 32, 0.8,  _CAT_SOPORTES),
    _SkuDef("136.097", "SOPORTE EXTINTOR 10 KG AUTO",                32,  8, 38, 1.2,  _CAT_SOPORTES),
    _SkuDef("136.098", "SOPORTE MURAL SIMPLE EXTINTOR",              22,  6, 26, 0.5,  _CAT_SOPORTES),
    _SkuDef("136.099", "SOPORTE MURAL REFORZADO EXTINTOR",           26,  8, 32, 0.8,  _CAT_SOPORTES),
    _SkuDef("136.100", "SOPORTE MURAL SIMPLE EXT. CO2",              22,  6, 26, 0.5,  _CAT_SOPORTES),
    _SkuDef("136.191", "FUNDA EXTINTOR 6 KG",                        26, 16,  6, 0.3,  _CAT_FUNDAS),
    _SkuDef("136.192", "FUNDA EXTINTOR 10 KG",                       32, 20,  6, 0.4,  _CAT_FUNDAS),
    _SkuDef("140.590", "CARRETE C/GABINETE 1X30MT RED HUMEDA",       60, 30, 60, 18.0, _CAT_GABINETES),
    _SkuDef("140.631", "SOPORTE REFORZADO CAMION 6KG",               34, 10, 40, 1.8,  _CAT_SOPORTES),
    _SkuDef("140.632", "SOPORTE REFORZADO CAMION 10KG",              40, 10, 46, 2.2,  _CAT_SOPORTES),
    _SkuDef("140.633", "CARRO PQS 25KG 90% EXANCO",                  60, 50,110, 46.0, _CAT_CARROS,     True, ExtinguisherAgent.PQS, 25.0),
    _SkuDef("140.634", "CARRO PQS 50KG 90% EXANCO",                  72, 56,135, 82.0, _CAT_CARROS,     True, ExtinguisherAgent.PQS, 50.0),
    _SkuDef("140.635", "CARRO CO2 10KG EXANCO",                      52, 40,105, 32.0, _CAT_CARROS,     True, ExtinguisherAgent.CO2, 10.0),
    _SkuDef("140.809", "EXTINTOR PQS ABC 2KG",                       12, 12, 42, 4.0,  _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 2.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("141.854", "MANGUERA EXTINTOR EXANCO 6 KG",              22, 10,  6, 0.3,  _CAT_MANGUERAS),
    _SkuDef("141.855", "MANGUERA EXTINTOR EXANCO 10 KG",             28, 10,  6, 0.4,  _CAT_MANGUERAS),
    _SkuDef("141.856", "VALVULA M30 HILO COMPLETO C/SIFON 4K",       16, 10, 16, 0.6,  _CAT_MANGUERAS),
    _SkuDef("141.857", "VALVULA M30 HIL CMP C/SIFON  6KG",           18, 12, 18, 0.8,  _CAT_MANGUERAS),
    _SkuDef("141.858", "VALVULA M30 HIL CMP C/SIFON 10KG",           22, 14, 22, 1.2,  _CAT_MANGUERAS),
    _SkuDef("141.859", "CINTILLO EXTINTOR",                           12,  6,  4, 0.05, _CAT_ACCESORIOS),
    _SkuDef("141.860", "SELLO EXTINTOR",                              13,  9,  1, 0.02, _CAT_ACCESORIOS),
    _SkuDef("141.921", "MANOMETRO EXTINTOR EXANCO",                   11,  6, 11, 0.15, _CAT_ACCESORIOS),
    _SkuDef("157.338", "SOPORTE EXTINTOR PISO",                       46, 22, 88, 6.0,  _CAT_SOPORTES),
    _SkuDef("157.339", "MANTA IGNIFUGA  1,8 X 1,2 M",                28, 28, 10, 2.0,  _CAT_FUNDAS),
    _SkuDef("157.340", "FUNDA CARRO 25KG",                            48, 16, 10, 0.8,  _CAT_FUNDAS),
    _SkuDef("157.341", "FUNDA CARRO 50KG",                            58, 20, 10, 1.0,  _CAT_FUNDAS),
    _SkuDef("163.027", "EXTINTOR PQS ABC   6KG EX   75% GETPRO",     17, 17, 60, 9.5,  _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 6.0,  _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("163.028", "EXTINTOR PQS ABC 10KG EX  75% GETPRO",       21, 21, 72, 14.5, _CAT_EXTINTORES, True, ExtinguisherAgent.PQS, 10.0, _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("163.682", "MANGUERA NITRILO 2 X 25M",                   42, 42, 22, 12.0, _CAT_MANGUERAS),
    _SkuDef("169.973", "CARRETE C/GABINETE 1X30MT PUERTA VIDRIO",    64, 32, 64, 20.0, _CAT_GABINETES),
    _SkuDef("171.134", "CARRETE C/GABINETE 1X25MT RED HUMEDA",       54, 28, 54, 15.0, _CAT_GABINETES),
    _SkuDef("171.135", "CARRETE 1X30MT RED HUMEDA",                   48, 24, 48, 12.0, _CAT_GABINETES),
    _SkuDef("171.136", "CARRETE 1X25MT RED HUMEDA",                   44, 22, 44, 10.0, _CAT_GABINETES),
    _SkuDef("171.137", "MANGUERA PARA CARRETE 1X30MT RED HUMEDA",    38, 38, 16, 8.5,  _CAT_MANGUERAS),
    _SkuDef("171.138", "MANGUERA PARA CARRETE 1X25MT RED HUMEDA",    34, 34, 14, 7.5,  _CAT_MANGUERAS),
    _SkuDef("180.403", "EXTINTOR AGUA 6 LT EXANCO",                   16, 16, 62, 9.0,  _CAT_EXTINTORES, True, ExtinguisherAgent.WATER, 6.0, _EXT_ORIENTATIONS, _EXT_GAP_FILL),
    _SkuDef("188.215", "MANTA IGNIFUGA  2,0 X 1,0 M",                32, 32, 12, 2.5,  _CAT_FUNDAS),
)

_PALETTE: tuple[str, ...] = (
    "#E53935", "#E91E63", "#AB47BC", "#5C6BC0",
    "#1E88E5", "#26C6DA", "#26A69A", "#66BB6A",
    "#9CCC65", "#FFCA28", "#FFA726", "#FF7043",
    "#8D6E63", "#78909C", "#BDBDBD", "#42A5F5",
)
_PALETTE_COLS = 8


class _ColorPaletteWidget(QWidget):
    """Grilla de swatches de color; clic para seleccionar."""

    def __init__(self, used_colors: tuple[str, ...] = (), parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._used = {c.lower() for c in used_colors}
        self._buttons: dict[str, QPushButton] = {}
        self._selected: str = _PALETTE[0]

        grid = QGridLayout(self)
        grid.setSpacing(5)
        grid.setContentsMargins(0, 0, 0, 0)
        for i, color in enumerate(_PALETTE):
            btn = QPushButton(self)
            btn.setFixedSize(28, 28)
            used = color.lower() in self._used
            btn.setToolTip(color + (" · ya en uso" if used else ""))
            btn.clicked.connect(lambda *, c=color: self._select(c))
            self._buttons[color] = btn
            grid.addWidget(btn, i // _PALETTE_COLS, i % _PALETTE_COLS)
        self._refresh_styles()

    def _select(self, color: str) -> None:
        self._selected = color
        self._refresh_styles()

    def _refresh_styles(self) -> None:
        for color, btn in self._buttons.items():
            selected = color == self._selected
            used = color.lower() in self._used
            if selected:
                border = "3px solid #1a1a1a"
            elif used:
                border = "2px solid #FB8C00"
            else:
                border = "2px solid rgba(0,0,0,0.18)"
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; border: {border}; border-radius: 5px; }}"
                f"QPushButton:hover {{ border: 2px solid #555; }}"
            )

    def select_first_unused(self) -> None:
        for c in _PALETTE:
            if c.lower() not in self._used:
                self._select(c)
                return
        self._select(_PALETTE[0])

    def selected_color(self) -> str:
        return self._selected


class InduproxSkuPickerDialog(QDialog):
    """Seleccionar un SKU del catálogo INDUPROX y asignarle un color."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        existing_colors: tuple[str, ...] = (),
        existing_skus: frozenset[str] = frozenset(),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Catálogo INDUPROX — Agregar SKU")
        self.resize(620, 500)
        self._result: LoadUnit | None = None
        self._existing_skus = {s.lower() for s in existing_skus}

        # ── Filtro de categoría ──────────────────────────────────────────
        filter_row = QHBoxLayout()
        cat_label = QLabel("Categoría:", self)
        cat_label.setStyleSheet("font-weight: 600;")
        self._cat_combo = QComboBox(self)
        for cat in CATEGORIES:
            self._cat_combo.addItem(cat)
        filter_row.addWidget(cat_label)
        filter_row.addWidget(self._cat_combo, 1)

        # ── Tabla de SKUs ────────────────────────────────────────────────
        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(["SKU", "Nombre", "Dimensiones (cm)", "Peso"])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        from PySide6.QtWidgets import QHeaderView
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        h.resizeSection(0, 80)
        h.resizeSection(2, 140)
        h.resizeSection(3, 70)

        # ── Paleta de colores ────────────────────────────────────────────
        color_label = QLabel("Color en el visor 3D:", self)
        color_label.setStyleSheet("font-weight: 600;")
        self._palette = _ColorPaletteWidget(existing_colors, self)
        self._palette.select_first_unused()

        # ── Botones ──────────────────────────────────────────────────────
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Agregar al catálogo")
            ok_btn.setProperty("class", "primary")
            ok_btn.setEnabled(False)
        self._ok_btn = ok_btn
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        # ── Layout ───────────────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self._table, 1)
        layout.addWidget(color_label)
        layout.addWidget(self._palette)
        layout.addWidget(self._button_box)

        # ── Señales ──────────────────────────────────────────────────────
        self._cat_combo.currentTextChanged.connect(self._rebuild_table)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        self._rebuild_table()

    def _rebuild_table(self) -> None:
        cat = self._cat_combo.currentText()
        self._table.setRowCount(0)
        self._table.blockSignals(True)
        for sku_def in _SKUS:
            if cat != _CAT_ALL and sku_def.category != cat:
                continue
            row = self._table.rowCount()
            self._table.insertRow(row)
            already = sku_def.sku.lower() in self._existing_skus
            dims = f"{sku_def.length_cm:.0f} × {sku_def.width_cm:.0f} × {sku_def.height_cm:.0f}"
            weight = f"{sku_def.weight_kg:.1f} kg"
            for col, text in enumerate((sku_def.sku, sku_def.name, dims, weight)):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, sku_def)
                if already:
                    item.setForeground(QColor("#AAAAAA"))
                    item.setToolTip("Ya existe en el catálogo")
                self._table.setItem(row, col, item)
        self._table.blockSignals(False)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if self._ok_btn is not None:
            self._ok_btn.setEnabled(bool(rows))

    def _selected_sku_def(self) -> _SkuDef | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_accept(self) -> None:
        sd = self._selected_sku_def()
        if sd is None:
            return
        color = self._palette.selected_color()
        self._result = LoadUnit(
            id=uuid4(),
            sku=sd.sku,
            name=sd.name,
            dimensions=Dimensions3D(sd.length_cm, sd.width_cm, sd.height_cm),
            weight_kg=sd.weight_kg,
            package_type=PackageType.INDIVIDUAL,
            units_per_package=1,
            max_stack_count=DEFAULT_MAX_STACK_COUNT,
            max_supported_weight_kg=None,
            allowed_orientation_codes=sd.orientation_codes,
            fragile=False,
            is_extinguisher=sd.is_extinguisher,
            extinguisher_agent=sd.extinguisher_agent,
            extinguisher_nominal_kg=sd.extinguisher_nominal_kg,
            color_hex=color,
            notes="",
        )
        self.accept()

    def result_load_unit(self) -> LoadUnit | None:
        return self._result
