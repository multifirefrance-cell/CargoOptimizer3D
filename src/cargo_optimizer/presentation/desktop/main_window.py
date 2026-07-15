"""Ventana principal de la aplicación de escritorio.

Desde la fase 5.1, `MainWindow` conecta la base de interfaz de la fase
5.0 con el motor real: "Ejecutar optimización" construye una
`PackingRequest` a partir de los paneles, la ejecuta en
`OptimizationWorker` (un `QThread` — nunca en el hilo de la interfaz) y
vuelca el `PackingResult` en los paneles de resultados. Sigue sin tocar
`domain`/`geometry`/`rules`/`optimization`: solo consume su API pública
(`PackingEngine`, `PackingRequest`, `PackingProgress`,
`CancellationToken`, vía `workers/optimization_worker.py`).

Desde la fase 6.1, el mismo `PackingResult` que ya llega a los paneles
de resultados se entrega también a `Packing3DViewer`
(`viewer/widget.py`), junto con el mismo mapping `UUID -> LoadUnit`
que ya se usaba para la tabla de no cargados — `MainWindow` sigue sin
importar nada de `viewer/` más allá de ese widget y su modelo visual
(`PlacementVisualModel`, solo para leerlo, nunca para construirlo).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from cargo_optimizer import __version__
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.optimization import GreedyExtremePointStrategy, PackingProgress, PackingRequest
from cargo_optimizer.optimization.exceptions import PackingRequestValidationError
from cargo_optimizer.presentation.desktop.icons import icon
from cargo_optimizer.presentation.desktop.panels.loading_space_form_panel import (
    LoadingSpaceFormPanel,
)
from cargo_optimizer.presentation.desktop.panels.log_panel import LogPanel
from cargo_optimizer.presentation.desktop.panels.product_table_panel import ProductTablePanel
from cargo_optimizer.presentation.desktop.panels.project_tree_panel import (
    SECTION_RESULTS,
    ProjectTreePanel,
)
from cargo_optimizer.presentation.desktop.panels.results_panel import ResultsPanel
from cargo_optimizer.presentation.desktop.panels.selection_details_panel import (
    SelectionDetailsPanel,
)
from cargo_optimizer.presentation.desktop.panels.unpacked_table_panel import UnpackedTablePanel
from cargo_optimizer.presentation.desktop.panels.warnings_panel import WarningsPanel
from cargo_optimizer.presentation.desktop.settings import AppSettings
from cargo_optimizer.presentation.desktop.style import THEME_DARK, THEME_LIGHT, apply_theme
from cargo_optimizer.presentation.desktop.viewer.widget import Packing3DViewer
from cargo_optimizer.presentation.desktop.workers.optimization_worker import OptimizationWorker

_NOT_IMPLEMENTED_MESSAGE_MS = 4000
_STATUS_MESSAGE_MS = 4000
_SPLITTER_MAIN = "main"
_SPLITTER_WORK_AREA = "workArea"
_SPLITTER_LEFT_WORK = "leftWork"
_HEADER_PRODUCT_TABLE = "productTable"
_ENGINE_LABEL = f"Motor: {GreedyExtremePointStrategy.name}"

STATE_READY = "listo"
STATE_PREPARING = "preparando"
STATE_OPTIMIZING = "optimizando"
STATE_CANCELLING = "cancelando"
STATE_FINISHED = "finalizado"
STATE_ERROR = "error"


class MainWindow(QMainWindow):
    """Ventana principal: menús, toolbar, paneles acoplables y barra de estado."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__()
        self._settings = settings or AppSettings()
        self._project_name = "Proyecto sin guardar"
        self._optimization_worker: OptimizationWorker | None = None
        self._last_load_units_by_id: dict[UUID, LoadUnit] = {}
        self._cancel_requested = False
        self._run_start_time = 0.0

        self.setWindowTitle(f"CargoOptimizer3D v{__version__}")
        self.resize(1280, 800)

        self._build_panels()
        self._build_dock_widgets()
        self._build_central_layout()
        self._build_actions()
        self._build_menu_bar()
        self._build_toolbar()
        self._build_status_bar()

        self._restore_ui_state()
        self.viewer_widget.set_dark_theme(self._settings.theme() == THEME_DARK)

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _build_panels(self) -> None:
        self.project_tree_panel = ProjectTreePanel(self)
        self.loading_space_form_panel = LoadingSpaceFormPanel(self)
        self.product_table_panel = ProductTablePanel(self)
        self.results_panel = ResultsPanel(self)
        self.unpacked_table_panel = UnpackedTablePanel(self)
        self.warnings_panel = WarningsPanel(self)
        self.log_panel = LogPanel(self)
        self.viewer_widget = Packing3DViewer(self)
        self.selection_details_panel = SelectionDetailsPanel(self)

        self.project_tree_panel.section_activated.connect(self._on_project_section_activated)
        self.viewer_widget.placement_selected.connect(self._on_placement_selected)

    def _build_dock_widgets(self) -> None:
        self.project_tree_dock = QDockWidget("Proyecto", self)
        self.project_tree_dock.setObjectName("projectTreeDock")
        self.project_tree_dock.setWidget(self.project_tree_panel)
        self.project_tree_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_tree_dock)

        self.selection_details_dock = QDockWidget("Detalles de selección", self)
        self.selection_details_dock.setObjectName("selectionDetailsDock")
        self.selection_details_dock.setWidget(self.selection_details_panel)
        self.selection_details_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.selection_details_dock)

    def _build_central_layout(self) -> None:
        self.left_work_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.left_work_splitter.setObjectName(_SPLITTER_LEFT_WORK)
        self.left_work_splitter.addWidget(self.loading_space_form_panel)
        self.left_work_splitter.addWidget(self.product_table_panel)
        self.left_work_splitter.setStretchFactor(1, 1)

        self.work_area_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.work_area_splitter.setObjectName(_SPLITTER_WORK_AREA)
        self.work_area_splitter.addWidget(self.left_work_splitter)
        self.work_area_splitter.addWidget(self.viewer_widget)
        self.work_area_splitter.setStretchFactor(0, 1)
        self.work_area_splitter.setStretchFactor(1, 1)

        self.results_tabs = QTabWidget(self)
        self.results_tabs.setObjectName("resultsTabs")
        self.results_tabs.addTab(self.results_panel, "Resumen")
        self.results_tabs.addTab(self.unpacked_table_panel, "No cargados")
        self.results_tabs.addTab(self.warnings_panel, "Avisos")
        self.results_tabs.addTab(self.log_panel, "Registro")

        self.main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.main_splitter.setObjectName(_SPLITTER_MAIN)
        self.main_splitter.addWidget(self.work_area_splitter)
        self.main_splitter.addWidget(self.results_tabs)
        self.main_splitter.setStretchFactor(0, 1)

        self.setCentralWidget(self.main_splitter)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _build_actions(self) -> None:
        self.action_new = self._make_action("new", "&Nuevo", "Ctrl+N", self._on_new_project)
        self.action_open = self._make_action("open", "&Abrir…", "Ctrl+O", self._on_open_project)
        self.action_save = self._make_action("save", "&Guardar", "Ctrl+S", self._on_save_project)
        self.action_save_as = self._make_action(
            "save", "Guardar &como…", "Ctrl+Shift+S", self._stub("Guardar como")
        )
        self.action_import = self._make_action("import", "&Importar…", None, self._on_import)
        self.action_export = self._make_action("import", "&Exportar…", None, self._stub("Exportar"))
        self.action_preferences = self._make_action(
            "preferences", "&Preferencias…", "Ctrl+,", self._stub("Preferencias")
        )
        self.action_exit = self._make_action("cancel", "&Salir", "Ctrl+Q", self.close)

        self.action_new_loading_space = self._make_action(
            "new", "&Nuevo espacio de carga", None, self._stub("Nuevo espacio de carga")
        )
        self.action_predefined_profiles = self._make_action(
            "open", "&Perfiles predefinidos…", None, self._stub("Perfiles predefinidos")
        )
        self.action_delete_loading_space = self._make_action(
            "cancel", "&Eliminar espacio de carga", None, self._stub("Eliminar espacio de carga")
        )

        self.action_new_product = self._make_action(
            "new",
            "&Nuevo producto",
            "Ctrl+Shift+N",
            self.product_table_panel.model.add_default_product,
        )
        self.action_delete_products = self._make_action(
            "cancel", "&Eliminar seleccionados", None, self.product_table_panel.remove_selected_rows
        )
        self.action_import_products = self._make_action(
            "import", "Importar &productos…", None, self._on_import
        )

        self.action_run_optimization = self._make_action(
            "optimize", "&Ejecutar optimización", "F5", self._on_run_optimization
        )
        self.action_cancel_optimization = self._make_action(
            "cancel", "&Cancelar", None, self._on_cancel_optimization
        )
        self.action_cancel_optimization.setEnabled(False)
        self.action_configure_optimization = self._make_action(
            "preferences", "&Configurar optimización…", None, self._stub("Configurar optimización")
        )
        self.action_show_results = self._make_action(
            "view3d", "&Ver resultados", None, self._on_show_results
        )

        self.action_toggle_project_dock = self.project_tree_dock.toggleViewAction()
        self.action_toggle_project_dock.setText("Panel de &proyecto")

        self.action_toggle_selection_details_dock = self.selection_details_dock.toggleViewAction()
        self.action_toggle_selection_details_dock.setText("Panel de &detalles")

        self.action_view_3d_focus = self._make_action(
            "view3d", "&Vista 3D", "Ctrl+3", self._on_toggle_3d_focus
        )
        self.action_view_3d_focus.setCheckable(True)

        self.action_reset_camera = self._make_action(
            "view3d", "&Restablecer cámara", "Ctrl+0", self._on_reset_camera
        )
        self.action_toggle_container_visible = self._make_action(
            "view3d",
            "Mostrar &espacio de carga",
            None,
            self._on_toggle_container_visible,
        )
        self.action_toggle_container_visible.setCheckable(True)
        self.action_toggle_container_visible.setChecked(True)
        self.action_toggle_boxes_visible = self._make_action(
            "view3d", "Mostrar &cajas", None, self._on_toggle_boxes_visible
        )
        self.action_toggle_boxes_visible.setCheckable(True)
        self.action_toggle_boxes_visible.setChecked(True)
        self.action_toggle_axes_visible = self._make_action(
            "view3d", "Mostrar &ejes", None, self._on_toggle_axes_visible
        )
        self.action_toggle_axes_visible.setCheckable(True)
        self.action_toggle_axes_visible.setChecked(True)

        self.action_light_theme = self._make_action(
            "preferences", "Tema &claro", None, lambda: self._set_theme(THEME_LIGHT)
        )
        self.action_dark_theme = self._make_action(
            "preferences", "Tema &oscuro", None, lambda: self._set_theme(THEME_DARK)
        )
        self.action_reset_layout = self._make_action(
            "open", "&Restaurar diseño de paneles", None, self._on_reset_layout
        )

        self.action_project_properties = self._make_action(
            "save", "&Propiedades del proyecto…", None, self._stub("Propiedades del proyecto")
        )
        self.action_event_log = self._make_action(
            "preferences", "&Registro de eventos", None, self._stub("Registro de eventos")
        )
        self.action_check_updates = self._make_action(
            "import", "&Comprobar actualizaciones", None, self._stub("Comprobar actualizaciones")
        )

        self.action_about = self._make_action(
            "preferences", "&Acerca de CargoOptimizer3D…", None, self._on_about
        )
        self.action_documentation = self._make_action(
            "open", "&Documentación", "F1", self._stub("Documentación")
        )

    def _make_action(
        self,
        icon_name: str,
        text: str,
        shortcut: str | None,
        slot: Callable[..., object],
    ) -> QAction:
        action = QAction(icon(icon_name), text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _stub(self, action_name: str) -> Callable[[], None]:
        def _handler() -> None:
            self.statusBar().showMessage(
                f"{action_name}: disponible en una próxima versión.", _NOT_IMPLEMENTED_MESSAGE_MS
            )

        return _handler

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&Archivo")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)
        file_menu.addSeparator()
        file_menu.addAction(self.action_import)
        file_menu.addAction(self.action_export)
        file_menu.addSeparator()
        file_menu.addAction(self.action_preferences)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        project_menu = menu_bar.addMenu("&Proyecto")
        project_menu.addAction(self.action_new_loading_space)
        project_menu.addAction(self.action_new_product)
        project_menu.addSeparator()
        project_menu.addAction(self.action_project_properties)

        loading_space_menu = menu_bar.addMenu("&Espacio de carga")
        loading_space_menu.addAction(self.action_new_loading_space)
        loading_space_menu.addAction(self.action_predefined_profiles)
        loading_space_menu.addSeparator()
        loading_space_menu.addAction(self.action_delete_loading_space)

        products_menu = menu_bar.addMenu("Pro&ductos")
        products_menu.addAction(self.action_new_product)
        products_menu.addAction(self.action_import_products)
        products_menu.addAction(self.action_export)
        products_menu.addSeparator()
        products_menu.addAction(self.action_delete_products)

        optimization_menu = menu_bar.addMenu("&Optimización")
        optimization_menu.addAction(self.action_run_optimization)
        optimization_menu.addAction(self.action_cancel_optimization)
        optimization_menu.addSeparator()
        optimization_menu.addAction(self.action_configure_optimization)
        optimization_menu.addAction(self.action_show_results)

        view_menu = menu_bar.addMenu("&Ver")
        view_menu.addAction(self.action_toggle_project_dock)
        view_menu.addAction(self.action_toggle_selection_details_dock)
        view_menu.addAction(self.action_view_3d_focus)
        view_menu.addSeparator()
        view_menu.addAction(self.action_reset_camera)
        view_menu.addAction(self.action_toggle_container_visible)
        view_menu.addAction(self.action_toggle_boxes_visible)
        view_menu.addAction(self.action_toggle_axes_visible)
        view_menu.addSeparator()
        view_menu.addAction(self.action_light_theme)
        view_menu.addAction(self.action_dark_theme)
        view_menu.addSeparator()
        view_menu.addAction(self.action_reset_layout)

        tools_menu = menu_bar.addMenu("&Herramientas")
        tools_menu.addAction(self.action_preferences)
        tools_menu.addAction(self.action_event_log)
        tools_menu.addAction(self.action_check_updates)

        help_menu = menu_bar.addMenu("A&yuda")
        help_menu.addAction(self.action_documentation)
        help_menu.addSeparator()
        help_menu.addAction(self.action_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principal", self)
        toolbar.setObjectName("mainToolBar")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)

        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_import)
        toolbar.addSeparator()
        toolbar.addAction(self.action_run_optimization)
        toolbar.addAction(self.action_cancel_optimization)
        toolbar.addSeparator()
        toolbar.addAction(self.action_view_3d_focus)
        toolbar.addSeparator()
        toolbar.addAction(self.action_preferences)

        self.addToolBar(toolbar)

    def _build_status_bar(self) -> None:
        bar = QStatusBar(self)
        self.setStatusBar(bar)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setObjectName("optimizationProgressBar")
        self._progress_bar.setMaximumWidth(180)
        self._progress_bar.setFormat("%v/%m")
        self._progress_bar.setVisible(False)

        self._progress_time_label = QLabel("", self)
        self._project_status_label = QLabel(self._project_name, self)
        self._engine_status_label = QLabel(_ENGINE_LABEL, self)
        self._state_status_label = QLabel("", self)
        self._set_state(STATE_READY)

        bar.addPermanentWidget(self._progress_time_label)
        bar.addPermanentWidget(self._progress_bar)
        bar.addPermanentWidget(self._project_status_label)
        bar.addPermanentWidget(self._engine_status_label)
        bar.addPermanentWidget(self._state_status_label)
        bar.showMessage("Listo.", _STATUS_MESSAGE_MS)

    # ------------------------------------------------------------------
    # Manejadores de acciones reales
    # ------------------------------------------------------------------

    def _on_new_project(self) -> None:
        model = self.product_table_panel.model
        model.remove_rows_at(list(range(model.rowCount())))
        self._project_name = "Proyecto sin guardar"
        self._project_status_label.setText(self._project_name)
        self.viewer_widget.clear_scene()
        self.selection_details_panel.clear()
        self.statusBar().showMessage("Nuevo proyecto creado.", _STATUS_MESSAGE_MS)

    def _on_open_project(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Abrir proyecto",
            self._settings.last_directory(),
            "Proyectos CargoOptimizer3D (*.cargo3d);;Todos los archivos (*)",
        )
        if not path:
            return
        self._remember_directory_of(path)
        self.statusBar().showMessage(
            "Apertura de proyectos: disponible en una próxima versión.", _NOT_IMPLEMENTED_MESSAGE_MS
        )

    def _on_save_project(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar proyecto",
            self._settings.last_directory(),
            "Proyectos CargoOptimizer3D (*.cargo3d)",
        )
        if not path:
            return
        self._remember_directory_of(path)
        self.statusBar().showMessage(
            "Guardado de proyectos: disponible en una próxima versión.", _NOT_IMPLEMENTED_MESSAGE_MS
        )

    def _on_import(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Importar",
            self._settings.last_directory(),
            "Hojas de cálculo (*.xlsx *.csv);;Todos los archivos (*)",
        )
        if not path:
            return
        self._remember_directory_of(path)
        self.statusBar().showMessage(
            "Importación: disponible en una próxima versión.", _NOT_IMPLEMENTED_MESSAGE_MS
        )

    def _remember_directory_of(self, file_path: str) -> None:
        self._settings.set_last_directory(str(Path(file_path).parent))

    def _on_project_section_activated(self, section: str) -> None:
        self.statusBar().showMessage(f"Sección: {section}", _STATUS_MESSAGE_MS)
        if section == SECTION_RESULTS:
            self._on_show_results()

    def _on_show_results(self) -> None:
        self.results_tabs.setCurrentWidget(self.results_panel)
        self.results_panel.setFocus()
        sizes = self.main_splitter.sizes()
        if len(sizes) == 2 and sizes[1] < 80:
            total = sum(sizes)
            self.main_splitter.setSizes([total - 200, 200])

    def _on_toggle_3d_focus(self, checked: bool) -> None:
        total = sum(self.work_area_splitter.sizes()) or 1
        if checked:
            self.work_area_splitter.setSizes([0, total])
        else:
            self.work_area_splitter.setSizes([total // 2, total - total // 2])

    def _on_reset_camera(self) -> None:
        self.viewer_widget.reset_camera()

    def _on_toggle_container_visible(self, checked: bool) -> None:
        self.viewer_widget.set_container_visible(checked)

    def _on_toggle_boxes_visible(self, checked: bool) -> None:
        self.viewer_widget.set_boxes_visible(checked)

    def _on_toggle_axes_visible(self, checked: bool) -> None:
        self.viewer_widget.set_axes_visible(checked)

    def _on_placement_selected(self, sequence_number: object) -> None:
        if not isinstance(sequence_number, int):
            self.selection_details_panel.clear()
            return
        visual = self.viewer_widget.find_placement_visual(sequence_number)
        if visual is None:
            self.selection_details_panel.clear()
            return
        self.selection_details_panel.display_placement(visual)

    def _set_theme(self, theme: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme)
        self.viewer_widget.set_dark_theme(theme == THEME_DARK)
        self._settings.set_theme(theme)

    def _on_reset_layout(self) -> None:
        total_width = self.work_area_splitter.width() or 1200
        self.work_area_splitter.setSizes([total_width // 2, total_width - total_width // 2])
        total_height = self.left_work_splitter.height() or 600
        self.left_work_splitter.setSizes([total_height // 3, total_height - total_height // 3])
        main_height = self.main_splitter.height() or 800
        self.main_splitter.setSizes([main_height - 160, 160])
        self.project_tree_dock.setFloating(False)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_tree_dock)
        self.project_tree_dock.show()
        self.statusBar().showMessage("Diseño de paneles restaurado.", _STATUS_MESSAGE_MS)

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de CargoOptimizer3D",
            f"<b>CargoOptimizer3D</b> v{__version__}<br>"
            "Software de optimización de carga 3D para espacios de carga universales.",
        )

    # ------------------------------------------------------------------
    # Ejecución del motor de optimización
    # ------------------------------------------------------------------

    def _build_packing_request(self) -> PackingRequest | None:
        """Lee espacio y productos de la interfaz; `None` si falta algo o son inválidos.

        Nunca lanza una excepción hacia el llamador: cualquier problema
        (espacio incompleto, sin productos, SKU duplicados tras editar la
        tabla, etc.) se explica con un `QMessageBox` y devuelve `None`
        para que `_on_run_optimization` simplemente no ejecute nada.
        """
        loading_space = self.loading_space_form_panel.build_loading_space()
        if loading_space is None:
            self._show_warning(
                "Espacio de carga incompleto",
                "Define un espacio de carga válido (nombre, dimensiones positivas y, si "
                "aplica, un peso máximo positivo) antes de optimizar.",
            )
            return None

        load_units = self.product_table_panel.model.load_units()
        if not load_units:
            self._show_warning(
                "Sin productos",
                "Agrega al menos un producto antes de ejecutar la optimización.",
            )
            return None

        try:
            return PackingRequest(loading_space=loading_space, load_units=load_units)
        except PackingRequestValidationError as exc:
            self._show_warning("Solicitud de optimización inválida", str(exc))
            return None

    def _on_run_optimization(self) -> None:
        if self._optimization_worker is not None and self._optimization_worker.isRunning():
            return

        request = self._build_packing_request()
        if request is None:
            return

        self._last_load_units_by_id = {unit.id: unit for unit in request.load_units}
        self._cancel_requested = False
        self._run_start_time = time.monotonic()

        self._set_state(STATE_PREPARING)
        self._set_running_controls_enabled(False)
        self.results_panel.clear()
        self.unpacked_table_panel.model.clear()
        self.warnings_panel.clear()
        self.viewer_widget.clear_scene()
        self.selection_details_panel.clear()
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_time_label.setText("0.0 s")
        self.log_panel.append_entry(
            f"Optimización iniciada: {len(request.load_units)} SKU(s) sobre "
            f"'{request.loading_space.name}'."
        )
        self.statusBar().showMessage("Optimizando…")

        worker = OptimizationWorker(request, self)
        worker.progress.connect(self._on_optimization_progress)
        worker.optimization_finished.connect(self._on_optimization_finished)
        worker.optimization_failed.connect(self._on_optimization_failed)
        worker.finished.connect(self._on_worker_thread_finished)
        self._optimization_worker = worker

        self._set_state(STATE_OPTIMIZING)
        worker.start()

    def _on_cancel_optimization(self) -> None:
        worker = self._optimization_worker
        if worker is None or not worker.isRunning():
            return
        self._cancel_requested = True
        worker.cancellation_token.cancel()
        self._set_state(STATE_CANCELLING)
        self.action_cancel_optimization.setEnabled(False)
        self.log_panel.append_entry("Cancelación solicitada por el usuario.")
        self.statusBar().showMessage("Cancelando…")

    def _on_optimization_progress(self, progress: PackingProgress) -> None:
        total = max(progress.total_instances, 1)
        self._progress_bar.setRange(0, total)
        self._progress_bar.setValue(min(progress.processed_instances, total))
        self._progress_time_label.setText(f"{progress.elapsed_seconds:.1f} s")

    def _on_optimization_finished(self, result: PackingResult) -> None:
        self._populate_results(result)
        self.selection_details_panel.clear()
        self.viewer_widget.display_result(result, self._last_load_units_by_id)
        self._set_state(STATE_FINISHED)
        message = (
            "Optimización cancelada." if self._cancel_requested else "Optimización finalizada."
        )
        self.log_panel.append_entry(
            f"{message} {result.packed_count}/{result.requested_count} cargadas en "
            f"{result.execution_time_seconds:.2f} s."
        )
        self.statusBar().showMessage(message, _STATUS_MESSAGE_MS)
        self._on_show_results()

    def _on_optimization_failed(self, message: str) -> None:
        self._set_state(STATE_ERROR)
        self.log_panel.append_entry(f"Error: {message}")
        self.statusBar().showMessage("Error durante la optimización.", _STATUS_MESSAGE_MS)
        self._show_error("Error de optimización", message)

    def _on_worker_thread_finished(self) -> None:
        self._progress_bar.setVisible(False)
        self._set_running_controls_enabled(True)
        worker = self._optimization_worker
        self._optimization_worker = None
        if worker is not None:
            worker.deleteLater()

    def _populate_results(self, result: PackingResult) -> None:
        self.results_panel.set_results(
            requested_count=result.requested_count,
            packed_count=result.packed_count,
            pending_count=result.unpacked_count,
            weight_kg=result.used_weight_kg,
            volume_m3=result.used_volume_cm3 / 1_000_000.0,
            utilization_percent=result.volume_utilization_percent,
            elapsed_seconds=result.execution_time_seconds,
            status="Cancelado" if self._cancel_requested else "Finalizado",
            warnings_count=len(result.warnings),
        )
        self.unpacked_table_panel.model.set_unpacked_units(
            result.unpacked_units, self._last_load_units_by_id
        )
        self.warnings_panel.set_warnings(result.warnings)

    def _set_running_controls_enabled(self, enabled: bool) -> None:
        for action in (
            self.action_run_optimization,
            self.action_new,
            self.action_open,
            self.action_new_product,
            self.action_delete_products,
            self.action_import,
            self.action_import_products,
        ):
            action.setEnabled(enabled)
        self.action_cancel_optimization.setEnabled(not enabled)
        self.product_table_panel.setEnabled(enabled)
        self.loading_space_form_panel.setEnabled(enabled)

    def _set_state(self, state: str) -> None:
        self._state_status_label.setText(f"Estado: {state}")

    def _show_warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------
    # Persistencia de interfaz (QSettings)
    # ------------------------------------------------------------------

    def _restore_ui_state(self) -> None:
        self._settings.restore_main_window_state(self)
        self._settings.restore_splitter_state(_SPLITTER_MAIN, self.main_splitter)
        self._settings.restore_splitter_state(_SPLITTER_WORK_AREA, self.work_area_splitter)
        self._settings.restore_splitter_state(_SPLITTER_LEFT_WORK, self.left_work_splitter)
        self._settings.restore_header_state(
            _HEADER_PRODUCT_TABLE, self.product_table_panel.table_view.horizontalHeader()
        )
        last_profile = self._settings.last_loading_space_profile()
        if last_profile:
            self.loading_space_form_panel.set_current_profile_name(last_profile)

    def _save_ui_state(self) -> None:
        self._settings.save_main_window_state(self)
        self._settings.save_splitter_state(_SPLITTER_MAIN, self.main_splitter)
        self._settings.save_splitter_state(_SPLITTER_WORK_AREA, self.work_area_splitter)
        self._settings.save_splitter_state(_SPLITTER_LEFT_WORK, self.left_work_splitter)
        self._settings.save_header_state(
            _HEADER_PRODUCT_TABLE, self.product_table_panel.table_view.horizontalHeader()
        )
        self._settings.set_last_loading_space_profile(
            self.loading_space_form_panel.current_profile_name()
        )
        self._settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (nombre impuesto por Qt)
        worker = self._optimization_worker
        if worker is not None and worker.isRunning():
            worker.cancellation_token.cancel()
            worker.wait(5000)
        self._save_ui_state()
        self.viewer_widget.shutdown()
        super().closeEvent(event)
