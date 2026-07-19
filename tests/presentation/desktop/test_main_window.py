"""Pruebas de `MainWindow`: creación, estructura y persistencia de QSettings."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QSizePolicy, QSplitter, QToolBar

from cargo_optimizer import __version__
from cargo_optimizer.presentation.desktop.main_window import MainWindow
from cargo_optimizer.presentation.desktop.settings import _KEY_MAIN_WINDOW_GEOMETRY, AppSettings

_MAX_WIDGET_HEIGHT = 16_777_215  # QWIDGETSIZE_MAX: valor por defecto sin maximumHeight fijado.


def _allow_close_without_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    """Responde "Descartar" al preguntar por cambios sin guardar (fase 7.0), ver `closeEvent`."""

    def _fake(*args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", staticmethod(_fake))


_EXPECTED_MENUS = (
    "&Archivo",
    "&Proyecto",
    "&Espacio de carga",
    "Pro&ductos",
    "&Optimización",
    "&Ver",
    "&Herramientas",
    "A&yuda",
)


def test_main_window_creates_without_error(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    assert window.windowTitle().startswith(f"CargoOptimizer3D v{__version__}")
    assert "Proyecto sin guardar" in window.windowTitle()
    window.close()


def test_main_window_has_all_required_menus(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    menu_titles = [action.text() for action in window.menuBar().actions()]
    for expected in _EXPECTED_MENUS:
        assert expected in menu_titles
    window.close()


def test_toolbar_has_required_actions(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    toolbar = window.findChild(QToolBar, "mainToolBar")
    assert toolbar is not None
    action_texts = {
        action.text().replace("&", "").replace("…", "")
        for action in toolbar.actions()
        if action.text()
    }
    for expected in (
        "Nuevo",
        "Abrir",
        "Guardar",
        "Importar Excel",
        "Ejecutar optimización",
        "Cancelar",
    ):
        assert expected in action_texts
    window.close()


def test_status_bar_shows_project_engine_and_state(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.statusBar() is not None
    assert window._project_status_label.text() != ""
    assert "Motor" in window._engine_status_label.text()
    assert "Estado" in window._state_status_label.text()
    window.close()


def test_unimplemented_action_shows_status_message(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window.action_check_updates.trigger()
    assert "próxima versión" in window.statusBar().currentMessage()
    window.close()


def test_new_product_action_adds_row_to_table(
    qapp: QApplication, app_settings: AppSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(app_settings)
    initial_rows = window.product_table_panel.model.rowCount()
    window.action_new_product.trigger()
    assert window.product_table_panel.model.rowCount() == initial_rows + 1
    _allow_close_without_saving(monkeypatch)
    window.close()


def test_close_event_persists_window_state(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    window.resize(1000, 700)
    expected_bytes = window.saveGeometry()
    window.close()

    stored_bytes = app_settings.qsettings.value(_KEY_MAIN_WINDOW_GEOMETRY)
    assert stored_bytes == expected_bytes

    restored = MainWindow(app_settings)  # no debe lanzar excepción al restaurar
    restored.close()


def test_toggle_theme_updates_settings(qapp: QApplication, app_settings: AppSettings) -> None:
    window = MainWindow(app_settings)
    window.action_dark_theme.trigger()
    assert app_settings.theme() == "dark"
    window.action_light_theme.trigger()
    assert app_settings.theme() == "light"
    window.close()


def test_selection_details_dock_hidden_by_default(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Rediseño "workspace operativo": el panel "Guía" desaparece por completo
    # y el dock de detalles de selección solo se muestra cuando el usuario
    # selecciona una caja en el visor 3D (nunca por defecto al arrancar).
    window = MainWindow(app_settings)
    window.show()
    assert not window.selection_details_dock.isVisible()
    window.close()


def test_work_area_splitter_holds_left_and_right_columns_in_order(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert isinstance(window.work_area_splitter, QSplitter)
    assert window.work_area_splitter.count() == 2
    assert window.work_area_splitter.widget(0) is window.left_work_container
    assert window.work_area_splitter.widget(1) is window.right_column_container
    window.close()


def test_work_area_splitter_is_not_collapsible_and_has_minimum_widths(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.work_area_splitter.childrenCollapsible() is False
    assert window.left_work_container.minimumWidth() > 0
    assert window.right_column_container.minimumWidth() > 0
    window.close()


def test_work_area_splitter_default_sizes_favor_the_viewer_column(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window.resize(1280, 800)
    window.show()
    qapp.processEvents()
    left_size, right_size = window.work_area_splitter.sizes()
    assert left_size > 0
    assert right_size > left_size
    window.close()


def test_results_tabs_live_under_the_right_column_not_full_window_width(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Mejoras UX: el panel de resultados ya no ocupa todo el ancho de la
    # ventana por debajo del panel izquierdo -- vive dentro de un splitter
    # vertical propio de la columna derecha, apilado bajo el visor 3D.
    window = MainWindow(app_settings)
    assert window.results_tabs.parentWidget() is window.viewer_results_splitter
    assert window.viewer_results_splitter.parentWidget() is window.right_column_container
    window.close()


def test_toggling_3d_focus_still_hides_the_left_column(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    window._on_toggle_3d_focus(True)
    assert window.left_work_container.isHidden() is True
    window._on_toggle_3d_focus(False)
    assert window.left_work_container.isHidden() is False
    window.close()


def test_product_table_panel_gets_all_extra_vertical_space_in_left_column(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Parte 4: "PRODUCTOS DE ESTA CARGA" debe crecer con el espacio
    # disponible, "ESPACIO DE CARGA" mantiene su altura natural.
    window = MainWindow(app_settings)
    left_layout = window.left_work_container.layout()
    assert left_layout is not None
    assert left_layout.stretch(0) == 0  # loading_space_summary_panel
    assert left_layout.stretch(1) == 1  # product_table_panel
    window.close()


def test_viewer_has_expanding_vertical_size_policy(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Mejoras UX (ajuste del visor): el visor 3D debe poder crecer para
    # ocupar el espacio sobrante de la columna derecha, no quedarse a su
    # tamaño mínimo mientras el splitter reparte el resto en otro sitio.
    window = MainWindow(app_settings)
    policy = window.viewer_widget.sizePolicy()
    assert policy.verticalPolicy() == QSizePolicy.Policy.Expanding
    assert policy.horizontalPolicy() == QSizePolicy.Policy.Expanding
    window.close()


def test_viewer_has_no_inappropriate_fixed_or_maximum_height(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.viewer_widget.maximumHeight() == _MAX_WIDGET_HEIGHT
    assert window.viewer_widget.minimumHeight() > 0
    window.close()


def test_viewer_results_splitter_stretch_factor_favors_the_viewer(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.viewer_results_splitter.widget(0) is window.viewer_widget
    assert window.viewer_results_splitter.widget(1) is window.results_tabs
    window.resize(1280, 900)
    window.show()
    qapp.processEvents()
    viewer_size, results_size = window.viewer_results_splitter.sizes()
    assert viewer_size > 0
    assert viewer_size > results_size
    window.close()


def test_viewer_results_splitter_is_not_collapsible_and_has_minimum_heights(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.viewer_results_splitter.childrenCollapsible() is False
    assert window.viewer_widget.minimumHeight() > 0
    assert window.results_tabs.minimumHeight() > 0
    window.close()


def test_stale_banner_visibility_does_not_change_viewer_splitter_sizes(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Parte 9: el aviso de "resultado invalidado" vive dentro de la pestaña
    # "Resumen", no altera el reparto de tamaños explícito del splitter.
    window = MainWindow(app_settings)
    window.resize(1280, 900)
    window.show()
    qapp.processEvents()
    sizes_before = list(window.viewer_results_splitter.sizes())

    window.results_panel.set_stale(True)
    qapp.processEvents()
    sizes_with_banner = list(window.viewer_results_splitter.sizes())

    window.results_panel.set_stale(False)
    qapp.processEvents()

    assert sizes_with_banner == sizes_before
    window.close()


def test_right_column_layout_contains_only_header_and_splitter(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Guarda estructural: ningún widget suelto/duplicado entre el
    # encabezado del espacio y el visor 3D (investigación de la franja
    # comprimida reportada -- no se encontró código que la produjera; esta
    # prueba fija que la columna derecha solo contiene exactamente estos
    # dos elementos).
    window = MainWindow(app_settings)
    layout = window.right_column_container.layout()
    assert layout is not None
    assert layout.count() == 2
    assert layout.itemAt(0).widget() is window.viewer_stats_header
    assert layout.itemAt(1).widget() is window.viewer_results_splitter
    window.close()


def test_horizontal_work_area_splitter_handle_has_configured_width(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    window = MainWindow(app_settings)
    assert window.work_area_splitter.handleWidth() >= 6
    assert window.viewer_results_splitter.handleWidth() >= 6
    window.close()


def test_window_resizes_without_error_at_several_sizes(
    qapp: QApplication, app_settings: AppSettings
) -> None:
    # Parte 9 (responsive): maximizar/restaurar/reducir no debe lanzar
    # excepciones ni dejar el splitter en un estado inconsistente.
    window = MainWindow(app_settings)
    window.show()
    for width, height in ((1920, 1080), (1024, 768), (900, 600)):
        window.resize(width, height)
        qapp.processEvents()
    assert window.left_work_container.width() > 0
    assert window.right_column_container.width() > 0
    window.close()
