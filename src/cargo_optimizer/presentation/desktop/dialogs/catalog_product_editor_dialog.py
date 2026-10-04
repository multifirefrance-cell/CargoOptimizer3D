"""`CatalogProductEditorDialog`: editor modal de un único `LoadUnit` (fase 7.1).

Construye y valida un `LoadUnit` real (nunca duplica las invariantes de
dominio: los errores de `LoadUnit.__post_init__` se muestran tal
cual). Se usa tanto para crear un producto de catálogo nuevo como para
editar uno existente (pasando `load_unit=` con los valores actuales).
También lo reutiliza `ProductTablePanel` (fase Beta 1.0) para dar de
alta/editar un `LoadUnit` del proyecto actual con un formulario
dedicado en vez de edición celda a celda en la tabla — mismo diálogo,
título parametrizable con `title`/`title_when_editing`.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID, uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFileDialog, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import (
    DEFAULT_MAX_STACK_COUNT,
    DEFAULT_ORIENTATION_CODES,
    LoadUnit,
)

_IMAGE_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp")
_IMAGE_SIZE = 140


class _ImageLabel(QLabel):
    """QLabel cuadrado clicable para mostrar/seleccionar la imagen del producto."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_IMAGE_SIZE, _IMAGE_SIZE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click para seleccionar imagen del producto")
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self.setPixmap(QPixmap())
        self.setText("📷\nAgregar\nimagen")
        self.setStyleSheet(
            "QLabel { border: 2px dashed #B0B5BC; border-radius: 8px; "
            "color: #999; font-size: 9pt; background: #F5F7FA; }"
        )

    def load_image(self, path: Path) -> bool:
        px = QPixmap(str(path))
        if px.isNull():
            return False
        self.setText("")
        self.setStyleSheet(
            "QLabel { border: 2px solid #B0B5BC; border-radius: 8px; background: #F5F7FA; }"
        )
        self.setPixmap(
            px.scaled(_IMAGE_SIZE, _IMAGE_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)
        )
        return True

    def clear_image(self) -> None:
        self._show_placeholder()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

_PACKAGE_TYPE_LABELS: dict[PackageType, str] = {
    PackageType.INDIVIDUAL: "Individual",
    PackageType.GROUPED_BOX: "Caja grupal",
    PackageType.PALLET: "Pallet",
    PackageType.DRUM: "Tambor",
    PackageType.CYLINDER: "Cilindro",
    PackageType.IRREGULAR_BOUNDING_BOX: "Carga irregular",
    PackageType.OTHER: "Otro",
}

_EXTINGUISHER_AGENT_LABELS: dict[ExtinguisherAgent, str] = {
    ExtinguisherAgent.PQS: "PQS",
    ExtinguisherAgent.CO2: "CO2",
    ExtinguisherAgent.WATER: "Agua",
    ExtinguisherAgent.FOAM: "Espuma",
    ExtinguisherAgent.WET_CHEMICAL: "Químico húmedo",
    ExtinguisherAgent.CLEAN_AGENT: "Agente limpio",
    ExtinguisherAgent.OTHER: "Otro",
}

_ORIENTATION_LABELS: dict[OrientationCode, str] = {
    OrientationCode.LWH_XYZ: "Original (largo-X, ancho-Y, alto-Z)",
    OrientationCode.WLH_XYZ: "Girada 90° en Z (ancho-X, largo-Y, alto-Z)",
    OrientationCode.LHW_XYZ: "Girada 90° en X (largo-X, alto-Y, ancho-Z)",
    OrientationCode.HWL_XYZ: "Girada 90° en Y (alto-X, ancho-Y, largo-Z)",
    OrientationCode.WHL_XYZ: "Ancho-X, alto-Y, largo-Z",
    OrientationCode.HLW_XYZ: "Alto-X, largo-Y, ancho-Z",
}

_DEFAULT_EXTINGUISHER_NOMINAL_KG = 1.0

_PALETTE: tuple[str, ...] = (
    "#E53935", "#E91E63", "#AB47BC", "#5C6BC0",
    "#1E88E5", "#26C6DA", "#26A69A", "#66BB6A",
    "#9CCC65", "#FFCA28", "#FFA726", "#FF7043",
    "#8D6E63", "#78909C", "#BDBDBD", "#42A5F5",
)
_PALETTE_COLS = 8


def _closest_palette_color(hex_color: str) -> str:
    for c in _PALETTE:
        if c.lower() == hex_color.lower():
            return c
    target = QColor(hex_color)
    if not target.isValid():
        return _PALETTE[0]
    best, best_dist = _PALETTE[0], float("inf")
    for c in _PALETTE:
        pc = QColor(c)
        dr, dg, db = target.red() - pc.red(), target.green() - pc.green(), target.blue() - pc.blue()
        dist = dr * dr + dg * dg + db * db
        if dist < best_dist:
            best_dist, best = dist, c
    return best


class _ColorPaletteWidget(QWidget):
    """Grilla de swatches de color; clic para seleccionar."""

    def __init__(self, used_colors: Sequence[str] = (), parent: QWidget | None = None) -> None:
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
                border = "3px solid rgba(255,255,255,0.9)"
            elif used:
                border = "2px solid #FB8C00"
            else:
                border = "2px solid rgba(0,0,0,0.18)"
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; border: {border}; border-radius: 5px; }}"
                f"QPushButton:hover {{ border: 2px solid #555; }}"
            )

    def select(self, hex_color: str) -> None:
        match = _closest_palette_color(hex_color)
        self._select(match)

    def selected_color(self) -> str:
        return self._selected


class CatalogProductEditorDialog(QDialog):
    """Formulario modal para crear o editar un producto del catálogo."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        load_unit: LoadUnit | None = None,
        title: str = "Nuevo producto de catálogo",
        title_when_editing: str = "Editar producto de catálogo",
        existing_colors: Sequence[str] = (),
        image_folder: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._editing_id: UUID | None = load_unit.id if load_unit is not None else None
        self._result_load_unit: LoadUnit | None = None
        self._image_folder = image_folder
        self._image_src_path: Path | None = None  # ruta del archivo seleccionado por el usuario
        self.setWindowTitle(title_when_editing if load_unit is not None else title)
        self.resize(520, 720)

        # ── Widget de imagen (arriba del formulario) ─────────────────────
        self._image_label = _ImageLabel(self)
        self._image_label.clicked.connect(self._on_image_clicked)

        self._sku_edit = QLineEdit(self)
        self._name_edit = QLineEdit(self)
        self._length_spin = self._make_dimension_spin()
        self._width_spin = self._make_dimension_spin()
        self._height_spin = self._make_dimension_spin()
        self._weight_spin = QDoubleSpinBox(self)
        self._weight_spin.setRange(0.0, 100_000.0)
        self._weight_spin.setSuffix(" kg")
        self._weight_spin.setDecimals(2)

        self._package_type_combo = QComboBox(self)
        for package_type, label in _PACKAGE_TYPE_LABELS.items():
            self._package_type_combo.addItem(label, package_type)

        self._units_per_package_spin = QSpinBox(self)
        self._units_per_package_spin.setRange(1, 10_000)

        self._max_stack_spin = QSpinBox(self)
        self._max_stack_spin.setRange(1, 100)

        self._priority_spin = QSpinBox(self)
        self._priority_spin.setRange(0, 99)
        self._priority_spin.setSpecialValueText("0 — automático (por volumen)")
        self._priority_spin.setToolTip(
            "0 = el algoritmo ordena este SKU por volumen (comportamiento automático).\n"
            "1–99 = posición en el contenedor: 1 queda al fondo, valores mayores quedan arriba."
        )

        self._no_max_supported_weight_check = QCheckBox("Sin límite", self)
        self._max_supported_weight_spin = QDoubleSpinBox(self)
        self._max_supported_weight_spin.setRange(0.0, 1_000_000.0)
        self._max_supported_weight_spin.setSuffix(" kg")
        self._no_max_supported_weight_check.toggled.connect(
            lambda checked: self._max_supported_weight_spin.setEnabled(not checked)
        )

        self._orientation_checks: dict[OrientationCode, QCheckBox] = {
            code: QCheckBox(label, self) for code, label in _ORIENTATION_LABELS.items()
        }

        self._fragile_check = QCheckBox("Frágil", self)

        self._is_extinguisher_check = QCheckBox("Es un extintor", self)
        self._extinguisher_agent_combo = QComboBox(self)
        for agent, label in _EXTINGUISHER_AGENT_LABELS.items():
            self._extinguisher_agent_combo.addItem(label, agent)
        self._extinguisher_nominal_spin = QDoubleSpinBox(self)
        self._extinguisher_nominal_spin.setRange(0.01, 1000.0)
        self._extinguisher_nominal_spin.setSuffix(" kg")
        self._is_extinguisher_check.toggled.connect(self._on_is_extinguisher_toggled)

        used = [c for c in existing_colors if c]
        self._palette_widget = _ColorPaletteWidget(used, self)
        self._notes_edit = QPlainTextEdit(self)
        self._notes_edit.setFixedHeight(60)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        ok_btn = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setProperty("class", "primary")

        self._build_layout()
        self._on_is_extinguisher_toggled(False)

        if load_unit is not None:
            self._populate_from(load_unit)
        else:
            used_lower = {c.lower() for c in existing_colors}
            first_unused = next((c for c in _PALETTE if c.lower() not in used_lower), _PALETTE[0])
            self._palette_widget.select(first_unused)
            # Orientaciones reducidas por defecto (fase OPT-17, ver
            # `DEFAULT_ORIENTATION_CODES`): un producto nuevo solo se
            # marca horizontal, largo paralelo al contenedor + su única
            # alternativa horizontal — nunca las 6 rotaciones. El
            # administrador habilita el resto a mano si el producto
            # concreto lo permite.
            for code, check in self._orientation_checks.items():
                check.setChecked(code in DEFAULT_ORIENTATION_CODES)
            # Mismo valor por defecto que `LoadUnit.max_stack_count`
            # (`DEFAULT_MAX_STACK_COUNT`): un producto nuevo nunca queda
            # "no apilable" por accidente — ver docstring del campo.
            self._max_stack_spin.setValue(DEFAULT_MAX_STACK_COUNT)

    @staticmethod
    def _make_dimension_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 5000.0)
        spin.setSuffix(" cm")
        spin.setDecimals(1)
        return spin

    def _build_layout(self) -> None:
        # ── Header: imagen a la izquierda, SKU+Nombre a la derecha ────────
        sku_name_form = QFormLayout()
        sku_name_form.setSpacing(8)
        sku_name_form.addRow("SKU", self._sku_edit)
        sku_name_form.addRow("Nombre", self._name_edit)

        header = QHBoxLayout()
        header.setSpacing(14)
        header.addWidget(self._image_label)
        header.addLayout(sku_name_form, 1)

        # ── Formulario principal (sin SKU/Nombre, ya están arriba) ────────
        form = QFormLayout()
        form.addRow("Largo", self._length_spin)
        form.addRow("Ancho", self._width_spin)
        form.addRow("Alto", self._height_spin)
        form.addRow("Peso", self._weight_spin)
        form.addRow("Tipo de empaque", self._package_type_combo)
        form.addRow("Unidades por paquete", self._units_per_package_spin)
        form.addRow("Límite máximo de apilamiento", self._max_stack_spin)
        form.addRow("Prioridad de carga", self._priority_spin)

        max_weight_row = QHBoxLayout()
        max_weight_row.addWidget(self._max_supported_weight_spin)
        max_weight_row.addWidget(self._no_max_supported_weight_check)
        form.addRow("Peso máximo soportado", max_weight_row)

        form.addRow("", self._fragile_check)
        form.addRow("Color", self._palette_widget)
        form.addRow("Notas", self._notes_edit)

        orientations_group = QGroupBox("Orientaciones permitidas", self)
        orientations_layout = QVBoxLayout(orientations_group)
        for check in self._orientation_checks.values():
            orientations_layout.addWidget(check)

        extinguisher_group = QGroupBox("Extintor", self)
        extinguisher_layout = QFormLayout(extinguisher_group)
        extinguisher_layout.addRow(self._is_extinguisher_check)
        extinguisher_layout.addRow("Agente", self._extinguisher_agent_combo)
        extinguisher_layout.addRow("Peso nominal", self._extinguisher_nominal_spin)

        scroll_content = QWidget(self)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addLayout(form)
        scroll_layout.addWidget(orientations_group)
        scroll_layout.addWidget(extinguisher_group)
        scroll_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._button_box)

    def _on_is_extinguisher_toggled(self, checked: bool) -> None:
        self._extinguisher_agent_combo.setEnabled(checked)
        self._extinguisher_nominal_spin.setEnabled(checked)

    # ── Imagen del producto ───────────────────────────────────────────────

    @staticmethod
    def _find_existing_image(image_folder: Path, sku: str) -> Path | None:
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            p = image_folder / f"{sku}{ext}"
            if p.exists():
                return p
        return None

    def _on_image_clicked(self) -> None:
        filter_str = "Imágenes (" + " ".join(_IMAGE_EXTS) + ")"
        path_str, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen del producto", "", filter_str)
        if not path_str:
            return
        path = Path(path_str)
        if self._image_label.load_image(path):
            self._image_src_path = path
        else:
            QMessageBox.warning(self, "Imagen inválida", "No se pudo cargar el archivo seleccionado.")

    def _save_image(self, sku: str) -> None:
        if self._image_src_path is None or self._image_folder is None:
            return
        self._image_folder.mkdir(parents=True, exist_ok=True)
        dest = self._image_folder / f"{sku}{self._image_src_path.suffix.lower()}"
        # Eliminar imágenes previas de ese SKU con otras extensiones
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            old = self._image_folder / f"{sku}{ext}"
            if old.exists() and old != dest:
                old.unlink(missing_ok=True)
        shutil.copy2(self._image_src_path, dest)

    def _populate_from(self, load_unit: LoadUnit) -> None:
        self._sku_edit.setText(load_unit.sku)
        self._name_edit.setText(load_unit.name)
        self._length_spin.setValue(load_unit.dimensions.length_cm)
        self._width_spin.setValue(load_unit.dimensions.width_cm)
        self._height_spin.setValue(load_unit.dimensions.height_cm)
        self._weight_spin.setValue(load_unit.weight_kg)
        index = self._package_type_combo.findData(load_unit.package_type)
        if index >= 0:
            self._package_type_combo.setCurrentIndex(index)
        self._units_per_package_spin.setValue(load_unit.units_per_package)
        self._max_stack_spin.setValue(load_unit.max_stack_count)
        self._priority_spin.setValue(load_unit.loading_priority)
        self._no_max_supported_weight_check.setChecked(load_unit.max_supported_weight_kg is None)
        self._max_supported_weight_spin.setValue(load_unit.max_supported_weight_kg or 0.0)
        for code, check in self._orientation_checks.items():
            check.setChecked(code in load_unit.allowed_orientation_codes)
        self._fragile_check.setChecked(load_unit.fragile)
        self._is_extinguisher_check.setChecked(load_unit.is_extinguisher)
        if load_unit.is_extinguisher:
            agent_index = self._extinguisher_agent_combo.findData(load_unit.extinguisher_agent)
            if agent_index >= 0:
                self._extinguisher_agent_combo.setCurrentIndex(agent_index)
            self._extinguisher_nominal_spin.setValue(
                load_unit.extinguisher_nominal_kg or _DEFAULT_EXTINGUISHER_NOMINAL_KG
            )
        self._palette_widget.select(load_unit.color_hex)
        self._notes_edit.setPlainText(load_unit.notes)
        if self._image_folder is not None:
            existing = self._find_existing_image(self._image_folder, load_unit.sku)
            if existing is not None:
                self._image_label.load_image(existing)

    def _build_load_unit(self) -> LoadUnit:
        allowed_codes = tuple(
            code for code, check in self._orientation_checks.items() if check.isChecked()
        )
        is_extinguisher = self._is_extinguisher_check.isChecked()
        # `currentData()` pasa por `QVariant`: un `StrEnum` (subclase de
        # `str`) vuelve como `str` plano, no como el enum original — se
        # reconstruye explícitamente para no guardar strings sueltos en un
        # campo tipado como enum (mismo hallazgo que
        # `loading_space_form_panel.py::build_loading_space`). Sin esto,
        # `ProductCatalogRepository.add()`/`update()` lanzan
        # `AttributeError` al intentar leer `.value` de un `str` plano.
        package_type = PackageType(self._package_type_combo.currentData())
        return LoadUnit(
            id=self._editing_id if self._editing_id is not None else uuid4(),
            sku=self._sku_edit.text().strip(),
            name=self._name_edit.text().strip(),
            dimensions=Dimensions3D(
                self._length_spin.value(), self._width_spin.value(), self._height_spin.value()
            ),
            weight_kg=self._weight_spin.value(),
            package_type=package_type,
            units_per_package=(
                1
                if package_type == PackageType.INDIVIDUAL
                else self._units_per_package_spin.value()
            ),
            max_stack_count=self._max_stack_spin.value(),
            max_supported_weight_kg=(
                None
                if self._no_max_supported_weight_check.isChecked()
                else self._max_supported_weight_spin.value()
            ),
            allowed_orientation_codes=allowed_codes or DEFAULT_ORIENTATION_CODES,
            fragile=self._fragile_check.isChecked(),
            is_extinguisher=is_extinguisher,
            extinguisher_agent=(
                ExtinguisherAgent(self._extinguisher_agent_combo.currentData())
                if is_extinguisher
                else ExtinguisherAgent.NOT_APPLICABLE
            ),
            extinguisher_nominal_kg=(
                self._extinguisher_nominal_spin.value() if is_extinguisher else None
            ),
            color_hex=self._palette_widget.selected_color(),
            notes=self._notes_edit.toPlainText(),
            loading_priority=self._priority_spin.value(),
        )

    def _on_accept(self) -> None:
        try:
            unit = self._build_load_unit()
        except DomainValidationError as exc:
            QMessageBox.warning(self, "Datos inválidos", str(exc))
            return
        self._save_image(unit.sku)
        self._result_load_unit = unit
        self.accept()

    def result_load_unit(self) -> LoadUnit | None:
        """El `LoadUnit` construido y válido tras aceptar, o `None` si se canceló."""
        return self._result_load_unit
