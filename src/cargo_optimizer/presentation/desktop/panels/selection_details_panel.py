"""Panel de detalles de la caja seleccionada en el visor 3D.

Solo lectura: muestra un `PlacementVisualModel`, nunca modifica datos
(ni de dominio ni del propio modelo visual). Se actualiza cuando se
selecciona una caja en el visor 3D, cuando se selecciona un Placement
desde una tabla futura, cuando se limpia la selección, o cuando se
ejecuta una nueva optimización — todo eso lo decide `MainWindow`,
llamando a `display_placement`/`clear`; este panel no escucha ninguna
señal por sí mismo.

Rediseño UX (auditoría "no mostrar información si no existe una caja
seleccionada"): sin selección se muestra un mensaje centrado en vez de
14 filas con "—"; con selección, la fila de peso nominal de extintor
se oculta (`QFormLayout.setRowVisible`) cuando la caja no es un
extintor — nunca un campo vacío que no aplica a la caja actual. Los
`QLabel` internos (`_sku_label`, etc.) siguen existiendo y actualizando
su texto exactamente igual que antes: solo cambia qué página del
`QStackedWidget` se muestra.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel

_EMPTY = "—"

_SI = "Sí"
_NO = "No"

_PLACEHOLDER_MESSAGE = "Selecciona una caja en el visor 3D\npara ver sus detalles."

_PAGE_EMPTY = 0
_PAGE_DETAILS = 1


class SelectionDetailsPanel(QWidget):
    """Detalle de solo lectura de la caja actualmente seleccionada."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("selectionDetailsPanel")

        self._color_swatch = QLabel(self)
        self._color_swatch.setFixedSize(14, 14)
        self._color_swatch.setStyleSheet("border-radius: 3px; border: 1px solid rgba(0,0,0,0.15);")
        self._sku_label = QLabel(_EMPTY, self)
        self._sku_label.setStyleSheet("font-weight: 700;")
        self._sku_row_widget = QWidget(self)
        sku_row = QHBoxLayout(self._sku_row_widget)
        sku_row.setContentsMargins(0, 0, 0, 0)
        sku_row.setSpacing(6)
        sku_row.addWidget(self._color_swatch)
        sku_row.addWidget(self._sku_label, 1)
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

        details_page = QWidget(self)
        self._form = QFormLayout(details_page)
        self._form.setContentsMargins(8, 4, 8, 4)
        # Grupo 1: Identificación
        self._form.addRow("SKU", self._sku_row_widget)
        self._form.addRow("Nombre", self._name_label)
        self._form.addRow("Instancia", self._instance_label)
        self._form.addRow(self._make_sep())
        # Grupo 2: Posición y orientación
        self._form.addRow("Secuencia de carga", self._sequence_label)
        self._form.addRow("Posición X/Y/Z (cm)", self._position_label)
        self._form.addRow("Largo/Ancho/Alto (cm)", self._dimensions_label)
        self._form.addRow("Orientación", self._orientation_label)
        self._form.addRow(self._make_sep())
        # Grupo 3: Propiedades físicas y logísticas
        self._form.addRow("Peso bruto", self._weight_label)
        self._form.addRow("Tipo de empaque", self._package_type_label)
        self._form.addRow("Unidades por paquete", self._units_per_package_label)
        self._form.addRow("Extintor", self._extinguisher_label)
        self._form.addRow("Peso nominal", self._extinguisher_nominal_label)
        self._form.addRow("Frágil", self._fragile_label)
        self._form.addRow("Apilamiento máximo", self._max_stack_label)
        self._form.addRow("Notas", self._notes_text)

        placeholder_page = QWidget(self)
        placeholder_label = QLabel(_PLACEHOLDER_MESSAGE, placeholder_page)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setWordWrap(True)
        placeholder_label.setStyleSheet("color: gray; font-size: 10.5pt;")
        placeholder_layout = QVBoxLayout(placeholder_page)
        placeholder_layout.addStretch(1)
        placeholder_layout.addWidget(placeholder_label)
        placeholder_layout.addStretch(1)

        details_scroll = QScrollArea(self)
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        details_scroll.setWidget(details_page)

        self._stack = QStackedWidget(self)
        self._stack.insertWidget(_PAGE_EMPTY, placeholder_page)
        self._stack.insertWidget(_PAGE_DETAILS, details_scroll)
        self._stack.setCurrentIndex(_PAGE_EMPTY)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    @staticmethod
    def _make_sep() -> QFrame:
        sep = QFrame()
        sep.setObjectName("formSectionSep")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        return sep

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
        self._sku_label.setStyleSheet("font-weight: 700;")
        self._color_swatch.setStyleSheet("border-radius: 3px; border: 1px solid rgba(0,0,0,0.15);")
        self._stack.setCurrentIndex(_PAGE_EMPTY)

    def display_placement(self, model: PlacementVisualModel) -> None:
        color = model.color_hex or "#CCCCCC"
        self._color_swatch.setStyleSheet(
            f"background: {color}; border-radius: 3px; border: 1px solid rgba(0,0,0,0.15);"
        )
        self._sku_label.setText(model.sku)
        self._sku_label.setStyleSheet("font-weight: 700;")
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
        self._form.setRowVisible(self._extinguisher_nominal_label, model.is_extinguisher)
        self._fragile_label.setText(_SI if model.fragile else _NO)
        self._max_stack_label.setText(str(model.max_stack_count))
        self._notes_text.setPlainText(model.notes)
        self._stack.setCurrentIndex(_PAGE_DETAILS)
