"""Panel de detalles de la caja seleccionada en el visor 3D.

Solo lectura: muestra un `PlacementVisualModel`, nunca modifica datos
(ni de dominio ni del propio modelo visual). Se actualiza cuando se
selecciona una caja en el visor 3D, cuando se selecciona un Placement
desde una tabla futura, cuando se limpia la selección, o cuando se
ejecuta una nueva optimización — todo eso lo decide `MainWindow`,
llamando a `display_placement`/`clear`; este panel no escucha ninguna
señal por sí mismo.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QPlainTextEdit, QWidget

from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel

_EMPTY = "—"

_SI = "Sí"
_NO = "No"


class SelectionDetailsPanel(QWidget):
    """Detalle de solo lectura de la caja actualmente seleccionada."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("selectionDetailsPanel")

        self._sku_label = QLabel(_EMPTY, self)
        self._name_label = QLabel(_EMPTY, self)
        self._instance_label = QLabel(_EMPTY, self)
        self._sequence_label = QLabel(_EMPTY, self)
        self._position_label = QLabel(_EMPTY, self)
        self._dimensions_label = QLabel(_EMPTY, self)
        self._orientation_label = QLabel(_EMPTY, self)
        self._weight_label = QLabel(_EMPTY, self)
        self._package_type_label = QLabel(_EMPTY, self)
        self._units_per_package_label = QLabel(_EMPTY, self)
        self._extinguisher_label = QLabel(_EMPTY, self)
        self._extinguisher_nominal_label = QLabel(_EMPTY, self)
        self._fragile_label = QLabel(_EMPTY, self)
        self._max_stack_label = QLabel(_EMPTY, self)
        self._notes_text = QPlainTextEdit(self)
        self._notes_text.setReadOnly(True)
        self._notes_text.setFixedHeight(60)

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addRow("SKU", self._sku_label)
        layout.addRow("Nombre", self._name_label)
        layout.addRow("Instancia", self._instance_label)
        layout.addRow("Secuencia de carga", self._sequence_label)
        layout.addRow("Posición X/Y/Z (cm)", self._position_label)
        layout.addRow("Largo/Ancho/Alto (cm)", self._dimensions_label)
        layout.addRow("Orientación", self._orientation_label)
        layout.addRow("Peso bruto", self._weight_label)
        layout.addRow("Tipo de empaque", self._package_type_label)
        layout.addRow("Unidades por paquete", self._units_per_package_label)
        layout.addRow("Extintor", self._extinguisher_label)
        layout.addRow("Peso nominal", self._extinguisher_nominal_label)
        layout.addRow("Frágil", self._fragile_label)
        layout.addRow("Apilamiento máximo", self._max_stack_label)
        layout.addRow("Notas", self._notes_text)

    def clear(self) -> None:
        for label in (
            self._sku_label,
            self._name_label,
            self._instance_label,
            self._sequence_label,
            self._position_label,
            self._dimensions_label,
            self._orientation_label,
            self._weight_label,
            self._package_type_label,
            self._units_per_package_label,
            self._extinguisher_label,
            self._extinguisher_nominal_label,
            self._fragile_label,
            self._max_stack_label,
        ):
            label.setText(_EMPTY)
        self._notes_text.setPlainText("")

    def display_placement(self, model: PlacementVisualModel) -> None:
        self._sku_label.setText(model.sku)
        self._name_label.setText(model.name)
        self._instance_label.setText(str(model.instance_number))
        self._sequence_label.setText(str(model.sequence_number))
        self._position_label.setText(
            f"{model.position[0]:.1f} / {model.position[1]:.1f} / {model.position[2]:.1f}"
        )
        self._dimensions_label.setText(
            f"{model.oriented_dimensions[0]:.1f} / "
            f"{model.oriented_dimensions[1]:.1f} / "
            f"{model.oriented_dimensions[2]:.1f}"
        )
        self._orientation_label.setText(model.orientation_code)
        self._weight_label.setText(f"{model.weight_kg:.1f} kg")
        self._package_type_label.setText(model.package_type)
        self._units_per_package_label.setText(str(model.units_per_package))
        self._extinguisher_label.setText(_SI if model.is_extinguisher else _NO)
        self._extinguisher_nominal_label.setText(
            f"{model.extinguisher_nominal_kg:.1f} kg"
            if model.extinguisher_nominal_kg is not None
            else _EMPTY
        )
        self._fragile_label.setText(_SI if model.fragile else _NO)
        self._max_stack_label.setText(str(model.max_stack_count))
        self._notes_text.setPlainText(model.notes)
