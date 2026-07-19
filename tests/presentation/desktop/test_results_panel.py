"""Pruebas de `ResultsPanel`: tarjetas KPI en una sola fila + resumen de línea.

La disposición en una sola fila (en vez de 2x3) es una corrección real,
no solo estética: con 2 filas, la altura mínima de este panel (que
entonces vivía en un `QSplitter` compitiendo por espacio con el área de
trabajo, hoy celdas fijas sin ningún separador arrastrable) superaba el
presupuesto reservado, forzando al workspace a exprimirse por debajo de
sus propios mínimos y provocando solapamiento visual en los paneles
vecinos (rediseño "workspace operativo"). `test_minimum_height_stays_compact`
es una prueba de regresión directa contra ese bug.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QFrame, QGridLayout, QLabel

from cargo_optimizer.presentation.desktop.panels.results_panel import ResultsPanel

_MAX_REASONABLE_MINIMUM_HEIGHT = 120


def test_kpi_tiles_are_laid_out_in_a_single_row(qapp: QApplication) -> None:
    panel = ResultsPanel()
    grid = panel.findChild(QGridLayout)
    assert grid is not None
    assert grid.rowCount() == 1
    assert grid.columnCount() == 6


def test_minimum_height_stays_compact(qapp: QApplication) -> None:
    panel = ResultsPanel()
    panel.set_results(
        requested_count=5,
        packed_count=5,
        pending_count=0,
        weight_kg=100.0,
        volume_m3=1.0,
        utilization_percent=50.0,
        elapsed_seconds=1.0,
        status="Completado",
        warnings_count=0,
    )
    assert panel.minimumSizeHint().height() < _MAX_REASONABLE_MINIMUM_HEIGHT


def test_set_results_populates_all_labels(qapp: QApplication) -> None:
    panel = ResultsPanel()
    panel.set_results(
        requested_count=10,
        packed_count=7,
        pending_count=3,
        weight_kg=250.5,
        volume_m3=2.345,
        utilization_percent=68.2,
        elapsed_seconds=1.23,
        status="Finalizado",
        warnings_count=2,
    )
    assert panel._requested_label.text() == "10"
    assert panel._packed_label.text() == "7"
    assert panel._pending_label.text() == "3"
    assert panel._weight_label.text() == "250.5 kg"
    assert panel._volume_label.text() == "2.345 m³"
    assert panel._utilization_label.text() == "68.2 %"
    assert panel._warnings_label.text() == "2"


def test_all_six_kpi_titles_wrap_words_instead_of_clipping(qapp: QApplication) -> None:
    # Corrección del bug real de truncado ("CANTIDAD PENDI...", sin unidad
    # visible): el título de cada tarjeta debe usar wordWrap en vez de
    # dejar que Qt recorte el texto que no cabe en el ancho de columna.
    panel = ResultsPanel()
    grid = panel.findChild(QGridLayout)
    assert grid is not None
    assert grid.count() == 6
    for index in range(grid.count()):
        tile = grid.itemAt(index).widget()
        assert isinstance(tile, QFrame)
        title_label = tile.layout().itemAt(0).widget()
        assert isinstance(title_label, QLabel)
        assert title_label.wordWrap() is True


def test_all_six_kpi_grid_columns_have_stretch_factor(qapp: QApplication) -> None:
    # Sin `columnStretch`, una ventana no muy ancha deja a las tarjetas con
    # menos ancho del que su contenido necesita -- causa real del truncado.
    panel = ResultsPanel()
    grid = panel.findChild(QGridLayout)
    assert grid is not None
    for column in range(grid.columnCount()):
        assert grid.columnStretch(column) >= 1


def test_time_label_populated_with_seconds_unit(qapp: QApplication) -> None:
    panel = ResultsPanel()
    panel.set_results(
        requested_count=10,
        packed_count=7,
        pending_count=3,
        weight_kg=250.5,
        volume_m3=2.345,
        utilization_percent=68.2,
        elapsed_seconds=1.23,
        status="Finalizado",
        warnings_count=2,
    )
    assert panel._time_label.text() == "1.23 s"


def test_clear_resets_all_labels(qapp: QApplication) -> None:
    panel = ResultsPanel()
    panel.set_results(
        requested_count=10,
        packed_count=7,
        pending_count=3,
        weight_kg=250.5,
        volume_m3=2.345,
        utilization_percent=68.2,
        elapsed_seconds=1.23,
        status="Finalizado",
        warnings_count=2,
    )
    panel.clear()
    assert panel._requested_label.text() == "—"
    assert panel._packed_label.text() == "—"
