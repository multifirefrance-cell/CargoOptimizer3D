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

from uuid import UUID, uuid4

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import ExtinguisherAgent, OrientationCode, PackageType
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.load_unit import DEFAULT_MAX_STACK_COUNT, LoadUnit

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


class CatalogProductEditorDialog(QDialog):
    """Formulario modal para crear o editar un producto del catálogo."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        load_unit: LoadUnit | None = None,
        title: str = "Nuevo producto de catálogo",
        title_when_editing: str = "Editar producto de catálogo",
    ) -> None:
        super().__init__(parent)
        self._editing_id: UUID | None = load_unit.id if load_unit is not None else None
        self._result_load_unit: LoadUnit | None = None
        self.setWindowTitle(title_when_editing if load_unit is not None else title)
        self.resize(520, 700)

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

        self._color_edit = QLineEdit(self)
        self._color_edit.setPlaceholderText("#RRGGBB")
        self._notes_edit = QPlainTextEdit(self)
        self._notes_edit.setFixedHeight(60)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)

        self._build_layout()
        self._on_is_extinguisher_toggled(False)

        if load_unit is not None:
            self._populate_from(load_unit)
        else:
            self._color_edit.setText("#CCCCCC")
            for check in self._orientation_checks.values():
                check.setChecked(True)
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
        form = QFormLayout()
        form.addRow("SKU", self._sku_edit)
        form.addRow("Nombre", self._name_edit)
        form.addRow("Largo", self._length_spin)
        form.addRow("Ancho", self._width_spin)
        form.addRow("Alto", self._height_spin)
        form.addRow("Peso", self._weight_spin)
        form.addRow("Tipo de empaque", self._package_type_combo)
        form.addRow("Unidades por paquete", self._units_per_package_spin)
        form.addRow("Límite máximo de apilamiento", self._max_stack_spin)

        max_weight_row = QHBoxLayout()
        max_weight_row.addWidget(self._max_supported_weight_spin)
        max_weight_row.addWidget(self._no_max_supported_weight_check)
        form.addRow("Peso máximo soportado", max_weight_row)

        form.addRow("", self._fragile_check)
        form.addRow("Color", self._color_edit)
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

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(orientations_group)
        layout.addWidget(extinguisher_group)
        layout.addWidget(self._button_box)

    def _on_is_extinguisher_toggled(self, checked: bool) -> None:
        self._extinguisher_agent_combo.setEnabled(checked)
        self._extinguisher_nominal_spin.setEnabled(checked)

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
        self._color_edit.setText(load_unit.color_hex)
        self._notes_edit.setPlainText(load_unit.notes)

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
            allowed_orientation_codes=allowed_codes or tuple(OrientationCode),
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
            color_hex=self._color_edit.text().strip() or "#CCCCCC",
            notes=self._notes_edit.toPlainText(),
        )

    def _on_accept(self) -> None:
        try:
            unit = self._build_load_unit()
        except DomainValidationError as exc:
            QMessageBox.warning(self, "Datos inválidos", str(exc))
            return
        self._result_load_unit = unit
        self.accept()

    def result_load_unit(self) -> LoadUnit | None:
        """El `LoadUnit` construido y válido tras aceptar, o `None` si se canceló."""
        return self._result_load_unit
