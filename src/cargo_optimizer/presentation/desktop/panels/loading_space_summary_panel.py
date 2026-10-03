"""Panel compacto del espacio de carga: Tipo, Perfil y resumen (rediseño UX).

Sustituye al `LoadingSpaceFormPanel` completo, que antes quedaba
siempre visible en la columna izquierda con los ~10 campos del
`LoadingSpace` (categoría, notas, posición de puerta, peso ilimitado,
etc.). Esta versión compacta solo muestra Tipo/Perfil y un resumen de
una línea; el formulario completo sigue existiendo tal cual y se abre
bajo demanda desde "Cambiar medidas…" (`LoadingSpaceEditorDialog`) — no
hay dos formularios ni dos fuentes de verdad, solo dos formas de
mostrar la misma.

Tipo agrupa los perfiles ya definidos en `loading_space_form_panel.py`
por su `LoadingSpaceCategory` real (nunca inventa una categoría nueva),
y Perfil lista los perfiles de ese tipo — "Personalizado" es su propio
"tipo" sin perfiles, igual que en el combo único original.
"""

from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    CATEGORY_LABELS,
    PROFILE_CUSTOM,
    loading_space_profiles,
)

_EMPTY = "—"
_TYPE_CUSTOM = PROFILE_CUSTOM


def _grouped_profile_names() -> dict[str, list[str]]:
    """Nombres de perfil agrupados por etiqueta de categoría, en el orden de `CATEGORY_LABELS`."""
    by_category: dict[LoadingSpaceCategory, list[str]] = defaultdict(list)
    for name, preset in loading_space_profiles().items():
        by_category[preset.category].append(name)
    grouped: dict[str, list[str]] = {}
    for category, label in CATEGORY_LABELS.items():
        if category in by_category:
            grouped[label] = by_category[category]
    return grouped


class LoadingSpaceSummaryPanel(QWidget):
    """Tipo + Perfil + resumen de una línea + "Cambiar medidas…"."""

    profile_selected = Signal(str)  # nombre de perfil resuelto (o PROFILE_CUSTOM)
    change_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingSpaceSummaryPanel")
        self.setAutoFillBackground(True)
        self._grouped = _grouped_profile_names()
        self._updating = False

        self._type_combo = QComboBox(self)
        self._type_combo.addItems([*self._grouped.keys(), _TYPE_CUSTOM])
        self._profile_combo = QComboBox(self)

        self._dimensions_label = QLabel(_EMPTY, self)
        self._dimensions_label.setStyleSheet("font-size: 13pt; font-weight: 600;")
        self._volume_label = QLabel(_EMPTY, self)
        self._volume_label.setProperty("class", "mutedLabel")
        self._weight_label = QLabel(_EMPTY, self)

        self._change_button = QPushButton("Cambiar medidas…", self)
        self._change_button.setToolTip("Abrir el editor completo del espacio de carga")

        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        self._change_button.clicked.connect(self.change_requested)

        form = QFormLayout()
        form.setSpacing(6)
        form.addRow("Tipo", self._type_combo)
        form.addRow("Perfil", self._profile_combo)

        dims_sub = QVBoxLayout()
        dims_sub.setSpacing(1)
        dims_sub.addWidget(self._dimensions_label)
        dims_sub.addWidget(self._volume_label)

        dims_row = QHBoxLayout()
        dims_row.addLayout(dims_sub, 1)
        dims_row.addWidget(self._weight_label)
        dims_row.addWidget(self._change_button)

        section_label = QLabel("ESPACIO DE CARGA", self)
        section_label.setStyleSheet(
            "font-weight: 700; font-size: 9pt; color: #999; letter-spacing: 0.5px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(section_label)
        layout.addLayout(form)
        layout.addLayout(dims_row)

        self._populate_profile_combo(self._type_combo.currentText())

    def _populate_profile_combo(self, type_label: str) -> None:
        # Guarda/restaura en vez de fijar `False` sin condiciones: si ya se
        # llama desde dentro de un bloque `_updating = True` (p. ej.
        # `set_current_profile`), pisar a `False` aquí dejaría sin proteger
        # el siguiente `setCurrentText` de esa función y filtraría una
        # emisión espuria de `profile_selected`.
        previous_updating = self._updating
        self._updating = True
        try:
            self._profile_combo.clear()
            if type_label == _TYPE_CUSTOM:
                self._profile_combo.addItem(PROFILE_CUSTOM)
                self._profile_combo.setEnabled(False)
            else:
                self._profile_combo.addItems(self._grouped.get(type_label, []))
                self._profile_combo.setEnabled(True)
        finally:
            self._updating = previous_updating

    def _on_type_changed(self, type_label: str) -> None:
        self._populate_profile_combo(type_label)
        if not self._updating:
            self._emit_current_profile()

    def _on_profile_changed(self, _profile_name: str) -> None:
        if not self._updating:
            self._emit_current_profile()

    def _emit_current_profile(self) -> None:
        profile_name = self._profile_combo.currentText()
        if profile_name:
            self.profile_selected.emit(profile_name)

    def set_current_profile(self, profile_name: str) -> None:
        """Sincroniza Tipo/Perfil desde el perfil real actual, sin volver a emitir la señal."""
        self._updating = True
        try:
            if profile_name == PROFILE_CUSTOM:
                self._type_combo.setCurrentText(_TYPE_CUSTOM)
                self._populate_profile_combo(_TYPE_CUSTOM)
                return
            for type_label, names in self._grouped.items():
                if profile_name in names:
                    self._type_combo.setCurrentText(type_label)
                    self._populate_profile_combo(type_label)
                    self._profile_combo.setCurrentText(profile_name)
                    return
        finally:
            self._updating = False

    def set_summary(self, space: LoadingSpace | None) -> None:
        if space is None:
            self._dimensions_label.setText(_EMPTY)
            self._volume_label.setText(_EMPTY)
            self._weight_label.setText(_EMPTY)
            return
        dims = space.internal_dimensions
        self._dimensions_label.setText(
            f"{dims.length_cm:.0f} × {dims.width_cm:.0f} × {dims.height_cm:.0f} cm"
        )
        volume_m3 = (dims.length_cm * dims.width_cm * dims.height_cm) / 1_000_000
        self._volume_label.setText(f"{volume_m3:.2f} m³ disponibles")
        self._weight_label.setText(
            f"{space.max_weight_kg:,.0f} kg".replace(",", ".")
            if space.max_weight_kg is not None
            else "Sin límite de peso"
        )
