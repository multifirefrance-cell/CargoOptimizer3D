"""Panel de formulario del Loading Space.

Un `QComboBox` de perfiles ofrece los tamaños habituales (contenedores
20'/40'/40HQ vía los perfiles orientativos ya definidos en
`cargo_optimizer.domain.loading_space.LoadingSpace`, y perfiles propios
de esta capa de presentación para camión/semirremolque/furgón/van/
bodega/otro, que el dominio no fija por no ser un estándar único). Los
campos permanecen bloqueados y muestran el valor del perfil elegido
hasta que el usuario selecciona "Personalizado", momento en el que se
habilitan para edición libre — así un perfil estándar nunca queda
editado por accidente.

No construye ni valida un `LoadingSpace` real todavía de forma
automática en cada tecleo (eso exigiría manejar estados intermedios
inválidos mientras el usuario escribe); `build_loading_space()` lo hace
bajo demanda y devuelve `None` si los valores actuales no son válidos.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QWidget,
)

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import DoorPosition, LoadingSpaceCategory
from cargo_optimizer.domain.exceptions import DomainValidationError
from cargo_optimizer.domain.loading_space import LoadingSpace

PROFILE_CUSTOM = "Personalizado"

_DOOR_LABELS: dict[DoorPosition, str] = {
    DoorPosition.FRONT: "Frontal",
    DoorPosition.REAR: "Trasera",
    DoorPosition.LEFT: "Izquierda",
    DoorPosition.RIGHT: "Derecha",
    DoorPosition.TOP: "Superior",
    DoorPosition.UNRESTRICTED: "Sin restricción",
}

CATEGORY_LABELS: dict[LoadingSpaceCategory, str] = {
    LoadingSpaceCategory.CONTAINER: "Contenedor",
    LoadingSpaceCategory.TRUCK: "Camión",
    LoadingSpaceCategory.VAN: "Furgón / van",
    LoadingSpaceCategory.TRAILER: "Semirremolque",
    LoadingSpaceCategory.WAREHOUSE: "Bodega",
    LoadingSpaceCategory.RACK: "Rack",
    LoadingSpaceCategory.OTHER: "Otro",
}


@dataclass(frozen=True)
class LoadingSpaceProfilePreset:
    name: str
    category: LoadingSpaceCategory
    dimensions: Dimensions3D
    door_position: DoorPosition
    max_weight_kg: float | None


def loading_space_profiles() -> dict[str, LoadingSpaceProfilePreset]:
    container_20 = LoadingSpace.standard_20ft_container()
    container_40 = LoadingSpace.standard_40ft_container()
    container_40hq = LoadingSpace.standard_40ft_high_cube_container()
    return {
        "Contenedor 20'": LoadingSpaceProfilePreset(
            container_20.name,
            container_20.category,
            container_20.internal_dimensions,
            container_20.door_position,
            container_20.max_weight_kg,
        ),
        "Contenedor 40'": LoadingSpaceProfilePreset(
            container_40.name,
            container_40.category,
            container_40.internal_dimensions,
            container_40.door_position,
            container_40.max_weight_kg,
        ),
        "Contenedor 40' HQ": LoadingSpaceProfilePreset(
            container_40hq.name,
            container_40hq.category,
            container_40hq.internal_dimensions,
            container_40hq.door_position,
            container_40hq.max_weight_kg,
        ),
        "Contenedor 20' Reefer": LoadingSpaceProfilePreset(
            "Contenedor 20' frigorífico (perfil orientativo)",
            LoadingSpaceCategory.CONTAINER,
            Dimensions3D(560.0, 228.0, 220.0),
            DoorPosition.REAR,
            27400.0,
        ),
        "Camión": LoadingSpaceProfilePreset(
            "Camión rígido (perfil orientativo)",
            LoadingSpaceCategory.TRUCK,
            Dimensions3D(600.0, 240.0, 240.0),
            DoorPosition.REAR,
            8000.0,
        ),
        "Semirremolque": LoadingSpaceProfilePreset(
            "Semirremolque (perfil orientativo)",
            LoadingSpaceCategory.TRAILER,
            Dimensions3D(1360.0, 245.0, 270.0),
            DoorPosition.REAR,
            24000.0,
        ),
        "Furgón": LoadingSpaceProfilePreset(
            "Furgón de reparto (perfil orientativo)",
            LoadingSpaceCategory.VAN,
            Dimensions3D(400.0, 200.0, 200.0),
            DoorPosition.REAR,
            1500.0,
        ),
        "Camión urbano": LoadingSpaceProfilePreset(
            "Camión de reparto urbano (perfil orientativo)",
            LoadingSpaceCategory.TRUCK,
            Dimensions3D(350.0, 200.0, 210.0),
            DoorPosition.REAR,
            3500.0,
        ),
        "Van": LoadingSpaceProfilePreset(
            "Van de carga (perfil orientativo)",
            LoadingSpaceCategory.VAN,
            Dimensions3D(300.0, 170.0, 170.0),
            DoorPosition.REAR,
            1000.0,
        ),
        "Pallet EUR": LoadingSpaceProfilePreset(
            "Pallet europeo EUR (perfil orientativo)",
            LoadingSpaceCategory.OTHER,
            Dimensions3D(120.0, 80.0, 170.0),
            DoorPosition.UNRESTRICTED,
            1000.0,
        ),
        "Pallet GMA": LoadingSpaceProfilePreset(
            "Pallet americano GMA (perfil orientativo)",
            LoadingSpaceCategory.OTHER,
            Dimensions3D(122.0, 102.0, 150.0),
            DoorPosition.UNRESTRICTED,
            1000.0,
        ),
        "Bodega": LoadingSpaceProfilePreset(
            "Bodega de almacenamiento (perfil orientativo)",
            LoadingSpaceCategory.WAREHOUSE,
            Dimensions3D(2000.0, 1500.0, 500.0),
            DoorPosition.UNRESTRICTED,
            None,
        ),
        "Otro": LoadingSpaceProfilePreset(
            "Espacio de carga",
            LoadingSpaceCategory.OTHER,
            Dimensions3D(500.0, 250.0, 250.0),
            DoorPosition.REAR,
            None,
        ),
    }


class LoadingSpaceFormPanel(QWidget):
    """Formulario del Loading Space actual, con perfiles predefinidos y modo personalizado."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingSpaceForm")
        self._profiles = loading_space_profiles()

        self._profile_combo = QComboBox(self)
        self._profile_combo.addItems([*self._profiles.keys(), PROFILE_CUSTOM])

        self._name_edit = QLineEdit(self)
        self._category_combo = QComboBox(self)
        for category, label in CATEGORY_LABELS.items():
            self._category_combo.addItem(label, category)

        self._length_spin = self._make_dimension_spin()
        self._width_spin = self._make_dimension_spin()
        self._height_spin = self._make_dimension_spin()

        self._no_weight_limit_check = QCheckBox("Sin límite de peso", self)
        self._max_weight_spin = QDoubleSpinBox(self)
        self._max_weight_spin.setRange(0.01, 500_000.0)
        self._max_weight_spin.setSuffix(" kg")
        self._max_weight_spin.setDecimals(1)

        self._door_combo = QComboBox(self)
        for door, label in _DOOR_LABELS.items():
            self._door_combo.addItem(label, door)

        self._notes_edit = QPlainTextEdit(self)
        self._notes_edit.setPlaceholderText("Notas (opcional)")
        self._notes_edit.setFixedHeight(60)

        self._locked_fields = (
            self._name_edit,
            self._category_combo,
            self._length_spin,
            self._width_spin,
            self._height_spin,
            self._no_weight_limit_check,
            self._max_weight_spin,
            self._door_combo,
            self._notes_edit,
        )

        self._build_layout()

        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        self._no_weight_limit_check.toggled.connect(self._on_no_weight_limit_toggled)

        self._profile_combo.currentTextChanged.connect(self.changed)
        self._name_edit.textChanged.connect(self.changed)
        self._category_combo.currentIndexChanged.connect(self.changed)
        self._length_spin.valueChanged.connect(self.changed)
        self._width_spin.valueChanged.connect(self.changed)
        self._height_spin.valueChanged.connect(self.changed)
        self._no_weight_limit_check.toggled.connect(self.changed)
        self._max_weight_spin.valueChanged.connect(self.changed)
        self._door_combo.currentIndexChanged.connect(self.changed)
        self._notes_edit.textChanged.connect(self.changed)

        self._profile_combo.setCurrentText("Contenedor 20'")
        self._apply_profile("Contenedor 20'")

    @staticmethod
    def _make_dimension_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 5000.0)
        spin.setSuffix(" cm")
        spin.setDecimals(1)
        return spin

    def _build_layout(self) -> None:
        form = QFormLayout(self)
        form.addRow("Perfil", self._profile_combo)
        form.addRow("Nombre", self._name_edit)
        form.addRow("Categoría", self._category_combo)
        form.addRow("Largo", self._length_spin)
        form.addRow("Ancho", self._width_spin)
        form.addRow("Alto", self._height_spin)
        form.addRow("", self._no_weight_limit_check)
        form.addRow("Peso máximo", self._max_weight_spin)
        form.addRow("Posición de puerta", self._door_combo)
        form.addRow("Notas", self._notes_edit)

    def _on_no_weight_limit_toggled(self, checked: bool) -> None:
        is_custom = self._profile_combo.currentText() == PROFILE_CUSTOM
        self._max_weight_spin.setEnabled(not checked and is_custom)

    def _on_profile_changed(self, profile_name: str) -> None:
        if profile_name == PROFILE_CUSTOM:
            for field in self._locked_fields:
                field.setEnabled(True)
            self._max_weight_spin.setEnabled(not self._no_weight_limit_check.isChecked())
            return
        self._apply_profile(profile_name)

    def _apply_profile(self, profile_name: str) -> None:
        profile = self._profiles[profile_name]
        self._name_edit.setText(profile.name)
        index = self._category_combo.findData(profile.category)
        if index >= 0:
            self._category_combo.setCurrentIndex(index)
        self._length_spin.setValue(profile.dimensions.length_cm)
        self._width_spin.setValue(profile.dimensions.width_cm)
        self._height_spin.setValue(profile.dimensions.height_cm)
        self._no_weight_limit_check.setChecked(profile.max_weight_kg is None)
        self._max_weight_spin.setValue(profile.max_weight_kg or 0.0)
        door_index = self._door_combo.findData(profile.door_position)
        if door_index >= 0:
            self._door_combo.setCurrentIndex(door_index)
        self._notes_edit.setPlainText("")

        for field in self._locked_fields:
            field.setEnabled(False)

    def current_profile_name(self) -> str:
        return self._profile_combo.currentText()

    def set_current_profile_name(self, profile_name: str) -> None:
        if profile_name and self._profile_combo.findText(profile_name) >= 0:
            self._profile_combo.setCurrentText(profile_name)

    def set_loading_space(self, space: LoadingSpace) -> None:
        """Vuelca `space` en el formulario en modo "Personalizado" (apertura de un proyecto).

        Un `LoadingSpace` guardado no coincide necesariamente con
        ninguno de los perfiles predefinidos, así que siempre se
        muestra como "Personalizado" — el mismo modo que ya desbloquea
        los campos para edición libre.
        """
        self._profile_combo.setCurrentText(PROFILE_CUSTOM)
        self._name_edit.setText(space.name)
        index = self._category_combo.findData(space.category)
        if index >= 0:
            self._category_combo.setCurrentIndex(index)
        self._length_spin.setValue(space.internal_dimensions.length_cm)
        self._width_spin.setValue(space.internal_dimensions.width_cm)
        self._height_spin.setValue(space.internal_dimensions.height_cm)
        self._no_weight_limit_check.setChecked(space.max_weight_kg is None)
        self._max_weight_spin.setValue(space.max_weight_kg or 0.0)
        door_index = self._door_combo.findData(space.door_position)
        if door_index >= 0:
            self._door_combo.setCurrentIndex(door_index)
        self._notes_edit.setPlainText(space.notes)

    def build_loading_space(self) -> LoadingSpace | None:
        """Construye el `LoadingSpace` actual, o `None` si los campos no son válidos todavía."""
        try:
            max_weight = (
                None if self._no_weight_limit_check.isChecked() else self._max_weight_spin.value()
            )
            return LoadingSpace(
                name=self._name_edit.text(),
                # `currentData()` pasa por `QVariant`: un `StrEnum` (subclase de
                # `str`) vuelve como `str` plano, no como el enum original —
                # se reconstruye explícitamente para no guardar strings sueltos
                # en un campo tipado como enum (ver serialización, fase 7.0).
                category=LoadingSpaceCategory(self._category_combo.currentData()),
                internal_dimensions=Dimensions3D(
                    self._length_spin.value(), self._width_spin.value(), self._height_spin.value()
                ),
                door_position=DoorPosition(self._door_combo.currentData()),
                max_weight_kg=max_weight,
                notes=self._notes_edit.toPlainText(),
            )
        except (DomainValidationError, ValueError):
            return None
