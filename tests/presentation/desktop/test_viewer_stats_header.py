"""Pruebas de `ViewerStatsHeader`: nombre/dimensiones + volumen/peso/utilización.

Rediseño UX ("workspace operativo"): el encargo original pedía que,
encima del visor 3D, se mostrara el espacio de carga elegido junto con
el volumen/peso/utilización del último resultado — este panel llenaba
un hueco real de la especificación que no se había implementado.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from cargo_optimizer.domain.dimensions import Dimensions3D
from cargo_optimizer.domain.enums import LoadingSpaceCategory
from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.presentation.desktop.panels.viewer_stats_header import ViewerStatsHeader


def _space() -> LoadingSpace:
    return LoadingSpace(
        name="Contenedor 20'",
        category=LoadingSpaceCategory.CONTAINER,
        internal_dimensions=Dimensions3D(589.0, 235.0, 239.0),
    )


def test_initial_state_shows_empty_placeholders(qapp: QApplication) -> None:
    header = ViewerStatsHeader()
    assert header._name_label.text() == "—"
    assert header._dimensions_label.text() == "—"
    assert "—" in header._volume_label.text()


def test_set_space_shows_name_and_dimensions(qapp: QApplication) -> None:
    header = ViewerStatsHeader()
    header.set_space(_space())
    assert header._name_label.text() == "Contenedor 20'"
    assert "589" in header._dimensions_label.text()
    assert "235" in header._dimensions_label.text()
    assert "239" in header._dimensions_label.text()


def test_set_space_none_clears_name_and_dimensions(qapp: QApplication) -> None:
    header = ViewerStatsHeader()
    header.set_space(_space())
    header.set_space(None)
    assert header._name_label.text() == "—"
    assert header._dimensions_label.text() == "—"


def test_set_result_stats_updates_volume_weight_utilization(qapp: QApplication) -> None:
    header = ViewerStatsHeader()
    header.set_result_stats(volume_m3=12.345, weight_kg=1500.0, utilization_percent=75.5)
    assert "12.35" in header._volume_label.text() or "12.34" in header._volume_label.text()
    assert "1.500" in header._weight_label.text() or "1500" in header._weight_label.text()
    assert "75.5" in header._utilization_label.text()


def test_clear_result_stats_resets_to_placeholders(qapp: QApplication) -> None:
    header = ViewerStatsHeader()
    header.set_result_stats(volume_m3=12.345, weight_kg=1500.0, utilization_percent=75.5)
    header.clear_result_stats()
    assert "—" in header._volume_label.text()
    assert "—" in header._weight_label.text()
    assert "—" in header._utilization_label.text()
