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
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from cargo_optimizer import __version__
from cargo_optimizer.domain.exceptions import DomainValidationError, DuplicateSkuError
from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.project import CargoProject
from cargo_optimizer.infrastructure.database import CatalogService, DatabaseError, RepositoryError
from cargo_optimizer.infrastructure.excel import (
    DuplicateResolution,
    ExcelError,
    ImportReport,
    ImportSelectionMode,
    RowError,
    build_catalog_preview,
    build_import_plan,
    build_import_report,
    canonical_columns_for,
    detect_column_mapping,
    detect_template_kind,
    export_catalog,
    export_import_report,
    export_packing_result,
    import_catalog,
    import_catalog_with_mapping,
    import_loading_spaces,
    import_packing_list,
    read_source_headers,
)
from cargo_optimizer.infrastructure.pdf import (
    BUILTIN_TEMPLATES,
    CompanyProfile,
    PdfError,
    ReportConfig,
    build_report_content,
    generate_report,
)
from cargo_optimizer.infrastructure.persistence import ProjectFileError, ProjectFileRepository
from cargo_optimizer.optimization import GreedyExtremePointStrategy, PackingProgress, PackingRequest
from cargo_optimizer.optimization.exceptions import PackingRequestValidationError
from cargo_optimizer.presentation.desktop.dialogs.bulk_import_dialog import BulkImportDialog
from cargo_optimizer.presentation.desktop.dialogs.column_mapping_dialog import ColumnMappingDialog
from cargo_optimizer.presentation.desktop.dialogs.duplicate_resolution_dialog import (
    DuplicateResolutionDialog,
)
from cargo_optimizer.presentation.desktop.dialogs.import_preview_dialog import ImportPreviewDialog
from cargo_optimizer.presentation.desktop.dialogs.loading_space_profiles_dialog import (
    LoadingSpaceProfilesDialog,
)
from cargo_optimizer.presentation.desktop.dialogs.product_catalog_dialog import (
    ProductCatalogDialog,
)
from cargo_optimizer.presentation.desktop.drag_drop import all_excel_paths, has_excel_url
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

_PROJECT_FILE_FILTER = "Proyectos CargoOptimizer3D (*.cargo3d)"
_PROJECT_FILE_EXTENSION = ".cargo3d"
_UNTITLED_PROJECT_NAME = "Proyecto sin guardar"
_RESULT_INVALIDATED_MESSAGE = "El resultado anterior fue invalidado porque el proyecto cambió."

STATE_READY = "listo"
STATE_PREPARING = "preparando"
STATE_OPTIMIZING = "optimizando"
STATE_CANCELLING = "cancelando"
STATE_FINISHED = "finalizado"
STATE_ERROR = "error"


class MainWindow(QMainWindow):
    """Ventana principal: menús, toolbar, paneles acoplables y barra de estado."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        catalog_service: CatalogService | None = None,
        catalog_error: str | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings or AppSettings()
        self._project_repository = ProjectFileRepository()
        self._catalog_service = catalog_service
        self._optimization_worker: OptimizationWorker | None = None
        self._last_load_units_by_id: dict[UUID, LoadUnit] = {}
        self._cancel_requested = False
        self._run_start_time = 0.0

        # Estado de proyecto (fase 7.0 — persistencia).
        self._current_project_id: UUID = uuid4()
        self._current_project_path: Path | None = None
        self._project_created_at: datetime | None = None
        self._project_notes: str = ""
        self._last_result: PackingResult | None = None
        self._is_dirty: bool = False
        self._result_stale: bool = False
        self._suspend_change_tracking: bool = False

        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._build_panels()
        self._build_dock_widgets()
        self._build_central_layout()
        self._build_actions()
        self._build_menu_bar()
        self._build_toolbar()
        self._build_status_bar()

        self._suspend_change_tracking = True
        try:
            self._restore_ui_state()
        finally:
            self._suspend_change_tracking = False
        self.viewer_widget.set_dark_theme(self._settings.theme() == THEME_DARK)
        self._update_window_title()

        self._apply_catalog_availability()
        if catalog_error is not None:
            self._show_warning(
                "Catálogo no disponible",
                "No se pudo inicializar la base de datos del catálogo de productos, "
                f"perfiles e historial:\n\n{catalog_error}\n\n"
                "La aplicación continúa en modo limitado: los proyectos .cargo3d "
                "siguen funcionando con normalidad, pero el catálogo, los perfiles "
                "guardados y el historial no estarán disponibles en esta sesión.",
            )

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

        self.loading_space_form_panel.changed.connect(self._on_project_data_changed)
        product_model = self.product_table_panel.model
        product_model.dataChanged.connect(self._on_project_data_changed)
        product_model.rowsInserted.connect(self._on_project_data_changed)
        product_model.rowsRemoved.connect(self._on_project_data_changed)
        product_model.modelReset.connect(self._on_project_data_changed)

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
        self.action_save = self._make_action(
            "save", "&Guardar", "Ctrl+S", lambda: self._on_save_project()
        )
        self.action_save_as = self._make_action(
            "save", "Guardar &como…", "Ctrl+Shift+S", lambda: self._on_save_project_as()
        )
        self.action_close_project = self._make_action(
            "cancel", "&Cerrar proyecto", None, self._on_close_project
        )
        self.action_import = self._make_action(
            "import", "Importar &Excel…", None, self._on_import_excel_auto
        )
        self.action_export = self._make_action(
            "import", "Exportar &Excel…", None, self._on_export_excel_menu
        )
        self.action_export_pdf = self._make_action(
            "import", "Exportar &PDF…", None, self._on_export_pdf
        )
        self.action_preferences = self._make_action(
            "preferences", "&Preferencias…", "Ctrl+,", self._stub("Preferencias")
        )
        self.action_exit = self._make_action("cancel", "&Salir", "Ctrl+Q", self.close)

        self.action_new_loading_space = self._make_action(
            "new", "&Nuevo espacio de carga", None, self._stub("Nuevo espacio de carga")
        )
        self.action_predefined_profiles = self._make_action(
            "open", "&Perfiles guardados…", None, self._on_open_profiles
        )
        self.action_save_as_profile = self._make_action(
            "save", "&Guardar espacio como perfil…", None, self._on_save_as_profile
        )
        self.action_import_loading_space_excel = self._make_action(
            "import", "&Importar desde Excel…", None, self._on_import_loading_space_excel
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
            "import", "Importar &productos…", None, self._on_import_excel_auto
        )
        self.action_open_catalog = self._make_action(
            "open", "&Catálogo de productos…", None, self._on_open_catalog
        )
        self.action_save_product_to_catalog = self._make_action(
            "save",
            "&Guardar seleccionado en catálogo",
            None,
            self._on_save_product_to_catalog,
        )
        self.action_add_from_catalog = self._make_action(
            "import", "Añadir &desde catálogo…", None, self._on_open_catalog
        )
        self.action_import_catalog_excel = self._make_action(
            "import", "Importar catálogo (&Excel)…", None, self._on_import_catalog_excel
        )
        self.action_import_catalog_excel_mapping = self._make_action(
            "import",
            "Importar con &mapeo de columnas…",
            None,
            self._on_import_catalog_excel_with_mapping,
        )
        self.action_bulk_import_catalog_excel = self._make_action(
            "import", "Importación &masiva de Excel…", None, self._on_bulk_import_catalog_excel
        )
        self.action_export_catalog_excel = self._make_action(
            "import", "Exportar catálogo (E&xcel)…", None, self._on_export_catalog_excel
        )
        self.action_import_packing_list_excel = self._make_action(
            "import", "Importar &Packing List…", None, self._on_import_packing_list_excel
        )
        self.action_export_result_excel = self._make_action(
            "import", "Exportar resul&tado…", None, self._on_export_result_excel
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
        self.menu_recent_projects = QMenu("Proyectos &recientes", self)
        self.menu_recent_projects.aboutToShow.connect(self._rebuild_recent_projects_menu)
        file_menu.addMenu(self.menu_recent_projects)
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_save_as)
        file_menu.addAction(self.action_close_project)
        file_menu.addSeparator()
        file_menu.addAction(self.action_import)
        file_menu.addAction(self.action_export)
        file_menu.addAction(self.action_export_pdf)
        file_menu.addSeparator()
        file_menu.addAction(self.action_preferences)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        project_menu = menu_bar.addMenu("&Proyecto")
        project_menu.addAction(self.action_new_loading_space)
        project_menu.addAction(self.action_new_product)
        project_menu.addSeparator()
        project_menu.addAction(self.action_import_packing_list_excel)
        project_menu.addAction(self.action_export_result_excel)
        project_menu.addSeparator()
        project_menu.addAction(self.action_project_properties)

        loading_space_menu = menu_bar.addMenu("&Espacio de carga")
        loading_space_menu.addAction(self.action_new_loading_space)
        loading_space_menu.addAction(self.action_predefined_profiles)
        loading_space_menu.addAction(self.action_save_as_profile)
        loading_space_menu.addAction(self.action_import_loading_space_excel)
        loading_space_menu.addSeparator()
        loading_space_menu.addAction(self.action_delete_loading_space)

        products_menu = menu_bar.addMenu("Pro&ductos")
        products_menu.addAction(self.action_new_product)
        products_menu.addAction(self.action_import_products)
        products_menu.addAction(self.action_export)
        products_menu.addSeparator()
        products_menu.addAction(self.action_open_catalog)
        products_menu.addAction(self.action_add_from_catalog)
        products_menu.addAction(self.action_save_product_to_catalog)
        products_menu.addSeparator()
        products_menu.addAction(self.action_import_catalog_excel)
        products_menu.addAction(self.action_import_catalog_excel_mapping)
        products_menu.addAction(self.action_bulk_import_catalog_excel)
        products_menu.addAction(self.action_export_catalog_excel)
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
        self._project_status_label = QLabel(self._project_display_name(), self)
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
        if not self._confirm_discard_unsaved_changes():
            return
        self._reset_to_blank_project()
        self.statusBar().showMessage("Nuevo proyecto creado.", _STATUS_MESSAGE_MS)

    def _on_close_project(self) -> None:
        if not self._confirm_discard_unsaved_changes():
            return
        self._reset_to_blank_project()
        self.statusBar().showMessage("Proyecto cerrado.", _STATUS_MESSAGE_MS)

    def _reset_to_blank_project(self) -> None:
        self._suspend_change_tracking = True
        try:
            model = self.product_table_panel.model
            model.remove_rows_at(list(range(model.rowCount())))
            self.results_panel.clear()
            self.unpacked_table_panel.model.clear()
            self.warnings_panel.clear()
            self.viewer_widget.clear_scene()
            self.selection_details_panel.clear()
        finally:
            self._suspend_change_tracking = False

        self._current_project_id = uuid4()
        self._current_project_path = None
        self._project_created_at = None
        self._project_notes = ""
        self._last_result = None
        self._last_load_units_by_id = {}
        self._result_stale = False
        self._mark_clean()

    def _on_open_project(self) -> None:
        if not self._confirm_discard_unsaved_changes():
            return
        path_str, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Abrir proyecto",
            self._settings.last_directory(),
            f"{_PROJECT_FILE_FILTER};;Todos los archivos (*)",
        )
        if not path_str:
            return
        self._open_project_from_path(Path(path_str))

    def _open_project_from_path(self, path: Path) -> None:
        try:
            loaded = self._project_repository.load(path)
        except ProjectFileError as exc:
            self._show_error("No se pudo abrir el proyecto", str(exc))
            return

        self._suspend_change_tracking = True
        try:
            self.loading_space_form_panel.set_loading_space(loaded.project.loading_space)
            self.product_table_panel.model.set_load_units(list(loaded.project.load_units))
            self._project_notes = loaded.project.notes
            self._current_project_id = loaded.project.id
            self._project_created_at = loaded.metadata.created_at
            self._last_load_units_by_id = {unit.id: unit for unit in loaded.project.load_units}
            self._last_result = loaded.project.latest_result
            self._result_stale = bool(loaded.presentation_state.get("result_stale", False))

            self.selection_details_panel.clear()
            if self._last_result is not None:
                self._populate_results(self._last_result)
                self.viewer_widget.display_result(self._last_result, self._last_load_units_by_id)
            else:
                self.results_panel.clear()
                self.unpacked_table_panel.model.clear()
                self.warnings_panel.clear()
                self.viewer_widget.clear_scene()
            self.results_panel.set_stale(self._result_stale)

            ui_state = loaded.presentation_state.get("ui_state")
            if isinstance(ui_state, dict):
                self._apply_ui_state(ui_state)
        finally:
            self._suspend_change_tracking = False

        self._current_project_path = path
        self._mark_clean()
        self._remember_directory_of(str(path))
        self._settings.add_recent_project_file(str(path))
        self._record_project_open_history(path)
        self.log_panel.append_entry(f"Proyecto abierto: {path}")
        self.statusBar().showMessage(f"Proyecto abierto: {path.name}", _STATUS_MESSAGE_MS)

    def _on_save_project(self) -> bool:
        if self._current_project_path is None:
            return self._on_save_project_as()
        return self._save_to_path(self._current_project_path)

    def _on_save_project_as(self) -> bool:
        path_str, _selected_filter = QFileDialog.getSaveFileName(
            self, "Guardar proyecto como", self._settings.last_directory(), _PROJECT_FILE_FILTER
        )
        if not path_str:
            return False
        path = Path(path_str)
        if path.suffix.lower() != _PROJECT_FILE_EXTENSION:
            path = path.with_suffix(_PROJECT_FILE_EXTENSION)
        return self._save_to_path(path)

    def _save_to_path(self, path: Path) -> bool:
        loading_space = self.loading_space_form_panel.build_loading_space()
        if loading_space is None:
            self._show_warning(
                "Espacio de carga incompleto",
                "Define un espacio de carga válido antes de guardar el proyecto.",
            )
            return False

        try:
            project = CargoProject(
                id=self._current_project_id,
                name=path.stem,
                loading_space=loading_space,
                load_units=self.product_table_panel.model.load_units(),
                latest_result=self._last_result,
                notes=self._project_notes,
            )
        except (DomainValidationError, DuplicateSkuError) as exc:
            self._show_warning("Proyecto inválido", str(exc))
            return False

        presentation_state: dict[str, Any] = {
            "result_stale": self._result_stale,
            "ui_state": self._collect_ui_state(),
        }
        try:
            metadata = self._project_repository.save(
                project,
                path,
                application_version=__version__,
                presentation_state=presentation_state,
                created_at=self._project_created_at,
            )
        except ProjectFileError as exc:
            self._show_error("No se pudo guardar el proyecto", str(exc))
            return False

        self._current_project_path = path
        self._project_created_at = metadata.created_at
        self._mark_clean()
        self._remember_directory_of(str(path))
        self._settings.add_recent_project_file(str(path))
        self._record_project_save_history(path)
        self.log_panel.append_entry(f"Proyecto guardado: {path}")
        self.statusBar().showMessage(f"Proyecto guardado: {path.name}", _STATUS_MESSAGE_MS)
        return True

    def _remember_directory_of(self, file_path: str) -> None:
        self._settings.set_last_directory(str(Path(file_path).parent))

    # ------------------------------------------------------------------
    # Importación y exportación profesional de Excel (fase 8.0)
    # ------------------------------------------------------------------

    def _prompt_open_excel_path(self, title: str) -> Path | None:
        path_str, _selected_filter = QFileDialog.getOpenFileName(
            self, title, self._settings.last_directory(), "Archivos Excel (*.xlsx)"
        )
        if not path_str:
            return None
        self._remember_directory_of(path_str)
        return Path(path_str)

    def _prompt_save_excel_path(self, title: str, default_name: str) -> Path | None:
        path_str, _selected_filter = QFileDialog.getSaveFileName(
            self,
            title,
            str(Path(self._settings.last_directory()) / default_name),
            "Archivos Excel (*.xlsx)",
        )
        if not path_str:
            return None
        self._remember_directory_of(path_str)
        path = Path(path_str)
        if path.suffix.casefold() != ".xlsx":
            path = path.with_suffix(".xlsx")
        return path

    def _prompt_save_pdf_path(self, title: str, default_name: str) -> Path | None:
        path_str, _selected_filter = QFileDialog.getSaveFileName(
            self,
            title,
            str(Path(self._settings.last_directory()) / default_name),
            "Archivos PDF (*.pdf)",
        )
        if not path_str:
            return None
        self._remember_directory_of(path_str)
        path = Path(path_str)
        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")
        return path

    def _on_import_excel_auto(self) -> None:
        path = self._prompt_open_excel_path("Importar Excel")
        if path is None:
            return
        try:
            kind = detect_template_kind(path)
        except ExcelError as exc:
            self._show_error("No se pudo leer el archivo Excel", str(exc))
            return

        if kind == "catalog":
            self._import_catalog_rows_into_project(path)
        elif kind == "packing_list":
            self._import_packing_list_from_path(path)
        elif kind == "loading_space":
            self._import_loading_spaces_from_path(path)
        else:
            self._show_warning(
                "Archivo no reconocido",
                f"'{path.name}' no coincide con ninguna plantilla oficial de "
                "CargoOptimizer3D (catálogo, packing list o espacio de carga). "
                "Verifica que la primera fila tenga las cabeceras esperadas.",
            )

    def _on_export_excel_menu(self) -> None:
        options = ["Catálogo de productos", "Resultado de la optimización"]
        choice, accepted = QInputDialog.getItem(
            self, "Exportar Excel", "¿Qué deseas exportar?", options, 0, False
        )
        if not accepted:
            return
        if choice == options[0]:
            self._on_export_catalog_excel()
        else:
            self._on_export_result_excel()

    def _import_catalog_rows_into_project(self, path: Path) -> None:
        """Importa un archivo con formato de catálogo directamente al proyecto actual.

        A diferencia de `_on_import_catalog_excel` (que guarda en el
        catálogo SQLite), esta ruta añade los productos como Load Units
        del proyecto abierto — mismo destino que "Añadir desde
        catálogo…" (fase 7.1), sin tocar la base de datos.
        """
        try:
            result = import_catalog(path)
        except ExcelError as exc:
            self._show_error("No se pudo importar el archivo", str(exc))
            return

        existing_skus = {
            unit.sku.casefold() for unit in self.product_table_panel.model.load_units()
        }
        to_add = []
        skipped: list[str] = []
        for unit in result.units:
            if unit.sku.casefold() in existing_skus:
                skipped.append(unit.sku)
                continue
            to_add.append(unit)
            existing_skus.add(unit.sku.casefold())

        if to_add:
            self.product_table_panel.model.add_units(to_add)
        self._report_import_outcome(
            path,
            imported_count=len(to_add),
            imported_label="producto(s) añadido(s) al proyecto",
            skipped_skus=skipped,
            row_errors=result.errors,
        )

    def _on_import_catalog_excel(self) -> None:
        if self._catalog_service is None:
            return
        path = self._prompt_open_excel_path("Importar catálogo (Excel)")
        if path is None:
            return
        self._run_and_report_smart_catalog_import(path, force_mapping_dialog=False)

    def _on_import_catalog_excel_with_mapping(self) -> None:
        if self._catalog_service is None:
            return
        path = self._prompt_open_excel_path("Importar catálogo con mapeo de columnas")
        if path is None:
            return
        self._run_and_report_smart_catalog_import(path, force_mapping_dialog=True)

    def _run_and_report_smart_catalog_import(
        self, path: Path, *, force_mapping_dialog: bool
    ) -> None:
        try:
            report = self._run_smart_catalog_import(
                path, interactive=True, force_mapping_dialog=force_mapping_dialog
            )
        except ExcelError as exc:
            self._show_error("No se pudo importar el catálogo", str(exc))
            return
        if report is None:
            return
        self._show_import_report(report)

    def _run_smart_catalog_import(
        self, path: Path, *, interactive: bool, force_mapping_dialog: bool = False
    ) -> ImportReport | None:
        """Mapeo -> vista previa -> resolución de duplicados -> escritura transaccional (fase 8.1).

        Devuelve `None` únicamente si el usuario cancela en algún paso
        interactivo — nunca ocurre cuando ``interactive=False``
        (importación masiva sin diálogos, con mapeo automático y
        "Actualizar" como resolución por defecto para cada SKU
        existente).
        """
        assert self._catalog_service is not None
        start_time = time.monotonic()
        headers = read_source_headers(path)
        mapping, unrecognized = detect_column_mapping(headers, "catalog")

        if interactive and (unrecognized or force_mapping_dialog):
            dialog = ColumnMappingDialog(
                self,
                target_kind="catalog",
                source_headers=headers,
                detected_mapping=mapping,
                profile_repository=self._catalog_service.import_mappings,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            mapping = dialog.result_mapping() or {}

        result = import_catalog_with_mapping(path, mapping)
        preview = build_catalog_preview(
            result,
            self._catalog_service.products.get_by_sku,
            column_count=len(canonical_columns_for("catalog")),
        )

        selection_mode: ImportSelectionMode = "all"
        selected_skus: frozenset[str] | None = None
        if interactive:
            preview_dialog = ImportPreviewDialog(self, preview=preview)
            if preview_dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            selection_mode = preview_dialog.result_selection_mode() or "all"
            selected_skus = preview_dialog.result_selected_skus()

        duplicate_resolutions: dict[str, DuplicateResolution] = {}
        if interactive and preview.existing_units:
            duplicate_dialog = DuplicateResolutionDialog(
                self, existing_units=preview.existing_units
            )
            if duplicate_dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            duplicate_resolutions = duplicate_dialog.result_resolutions() or {}

        plan = build_import_plan(
            preview,
            self._catalog_service.products.get_by_sku,
            selection_mode=selection_mode,
            selected_skus=selected_skus,
            duplicate_resolutions=duplicate_resolutions,
        )
        self._catalog_service.products.apply_bulk(to_add=plan.to_add, to_update=plan.to_update)

        elapsed = time.monotonic() - start_time
        return build_import_report(
            source_name=path.name, preview=preview, plan=plan, elapsed_seconds=elapsed
        )

    def _show_import_report(self, report: ImportReport) -> None:
        message = (
            f"Archivo: {report.source_name}\n"
            f"Filas leídas: {report.rows_read}\n"
            f"Importadas: {report.imported_count}\n"
            f"Actualizadas: {report.updated_count}\n"
            f"Duplicadas: {report.duplicate_count}\n"
            f"Ignoradas: {report.ignored_count}\n"
            f"Errores: {report.error_count}\n"
            f"Tiempo: {report.elapsed_seconds:.2f} s"
        )
        response = QMessageBox.question(
            self,
            "Importación completada",
            message + "\n\n¿Guardar el informe como Excel?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            report_path = self._prompt_save_excel_path(
                "Guardar informe de importación", "Informe_importacion.xlsx"
            )
            if report_path is not None:
                export_import_report(report, report_path)

    def _on_bulk_import_catalog_excel(self) -> None:
        if self._catalog_service is None:
            return
        dialog = BulkImportDialog(self, import_one=self._bulk_import_one_catalog_file)
        dialog.exec()

    def _bulk_import_one_catalog_file(self, path: Path) -> ImportReport:
        report = self._run_smart_catalog_import(path, interactive=False)
        assert report is not None  # interactive=False nunca cancela
        return report

    def _on_catalog_dialog_excel_dropped(self, path: Path, dialog: ProductCatalogDialog) -> None:
        """Callback de arrastrar y soltar sobre `ProductCatalogDialog` — importa al catálogo."""
        try:
            report = self._run_smart_catalog_import(path, interactive=True)
        except ExcelError as exc:
            self._show_error("No se pudo importar el catálogo", str(exc))
            return
        if report is None:
            return
        dialog.refresh()
        self._show_import_report(report)

    def _report_import_outcome(
        self,
        path: Path,
        *,
        imported_count: int,
        imported_label: str,
        skipped_skus: list[str],
        row_errors: tuple[RowError, ...],
    ) -> None:
        """Reporta el resultado de una importación; nunca oculta filas inválidas o SKU omitidos."""
        parts = [f"{imported_count} {imported_label} desde '{path.name}'."]
        if skipped_skus:
            parts.append("SKU ya existentes, no importados: " + ", ".join(skipped_skus))
        if row_errors:
            parts.append(
                "Filas con error (no importadas):\n"
                + "\n".join(f"  Fila {e.row_number}: {e.message}" for e in row_errors)
            )
        if skipped_skus or row_errors:
            self._show_warning("Importación con avisos", "\n\n".join(parts))
        else:
            self.statusBar().showMessage(parts[0], _STATUS_MESSAGE_MS)

    def _on_export_catalog_excel(self) -> None:
        if self._catalog_service is None:
            return
        units = self._catalog_service.products.list_active()
        if not units:
            self._show_warning("Catálogo vacío", "No hay productos activos en el catálogo.")
            return
        path = self._prompt_save_excel_path("Exportar catálogo", "Catalogo.xlsx")
        if path is None:
            return
        try:
            export_catalog(units, path)
        except ExcelError as exc:
            self._show_error("No se pudo exportar el catálogo", str(exc))
            return
        self.statusBar().showMessage(
            f"Catálogo exportado a '{path.name}' ({len(units)} producto(s)).", _STATUS_MESSAGE_MS
        )

    def _import_packing_list_from_path(self, path: Path) -> None:
        if self._catalog_service is None:
            self._show_warning(
                "Catálogo no disponible",
                "Importar un Packing List requiere el catálogo de productos, "
                "que no está disponible en modo limitado.",
            )
            return
        try:
            result = import_packing_list(path, self._catalog_service.products.get_by_sku)
        except ExcelError as exc:
            self._show_error("No se pudo importar el Packing List", str(exc))
            return

        if result.missing_skus:
            response = QMessageBox.question(
                self,
                "SKU no encontrados en el catálogo",
                "Los siguientes SKU del Packing List no existen en el catálogo:\n\n"
                + ", ".join(result.missing_skus)
                + "\n\n¿Deseas continuar e importar solo los productos encontrados?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if response == QMessageBox.StandardButton.Cancel:
                return

        existing_skus = {
            unit.sku.casefold() for unit in self.product_table_panel.model.load_units()
        }
        to_add = []
        skipped: list[str] = []
        for unit in result.resolved_units:
            if unit.sku.casefold() in existing_skus:
                skipped.append(unit.sku)
                continue
            to_add.append(unit)
            existing_skus.add(unit.sku.casefold())

        if to_add:
            self.product_table_panel.model.add_units(to_add)
        self._report_import_outcome(
            path,
            imported_count=len(to_add),
            imported_label="producto(s) añadido(s) desde el Packing List",
            skipped_skus=skipped,
            row_errors=result.errors,
        )

    def _on_import_packing_list_excel(self) -> None:
        if self._catalog_service is None:
            return
        path = self._prompt_open_excel_path("Importar Packing List")
        if path is None:
            return
        self._import_packing_list_from_path(path)

    def _on_export_result_excel(self) -> None:
        if self._last_result is None:
            self._show_warning(
                "Sin resultado", "Ejecuta una optimización antes de exportar el resultado."
            )
            return
        path = self._prompt_save_excel_path("Exportar resultado", "Resultado_optimizacion.xlsx")
        if path is None:
            return
        try:
            export_packing_result(
                self._last_result,
                self._last_load_units_by_id,
                path,
                application_version=__version__,
            )
        except ExcelError as exc:
            self._show_error("No se pudo exportar el resultado", str(exc))
            return
        self.statusBar().showMessage(f"Resultado exportado a '{path.name}'.", _STATUS_MESSAGE_MS)

    def _on_export_pdf(self) -> None:
        """Genera uno de los cinco informes PDF oficiales (fase 9.1, `docs/PdfReports.md`).

        La captura del visor 3D es siempre opcional: si no está
        disponible (`export_screenshot_png()` devuelve `None`), el
        informe se genera igual, sin esa sección — nunca es un motivo
        de error.
        """
        if self._last_result is None:
            self._show_warning(
                "Sin resultado", "Ejecuta una optimización antes de exportar un informe PDF."
            )
            return

        options = [template.display_name for template in BUILTIN_TEMPLATES]
        choice, accepted = QInputDialog.getItem(
            self, "Exportar PDF", "Tipo de informe:", options, 0, False
        )
        if not accepted:
            return
        template = next(t for t in BUILTIN_TEMPLATES if t.display_name == choice)

        default_name = f"{self._project_display_name()}_{template.key}.pdf"
        path = self._prompt_save_pdf_path("Exportar PDF", default_name)
        if path is None:
            return

        content = build_report_content(
            self._last_result,
            self._last_load_units_by_id,
            project_name=self._project_display_name(),
            application_version=__version__,
            viewer_screenshot_png=self.viewer_widget.export_screenshot_png(),
        )
        config = ReportConfig(company=CompanyProfile(name="CargoOptimizer3D"))
        try:
            generate_report(content, template, config, path)
        except PdfError as exc:
            self._show_error("No se pudo generar el informe PDF", str(exc))
            return
        self.statusBar().showMessage(f"Informe PDF exportado a '{path.name}'.", _STATUS_MESSAGE_MS)

    def _import_loading_spaces_from_path(self, path: Path) -> None:
        try:
            result = import_loading_spaces(path)
        except ExcelError as exc:
            self._show_error("No se pudo importar el archivo", str(exc))
            return

        if result.errors:
            self._show_warning(
                "Filas con error",
                "Las siguientes filas no se pudieron importar:\n\n"
                + "\n".join(f"Fila {e.row_number}: {e.message}" for e in result.errors),
            )
        if not result.spaces:
            return

        if len(result.spaces) == 1:
            chosen = result.spaces[0]
        else:
            names = [space.name for space in result.spaces]
            name, accepted = QInputDialog.getItem(
                self,
                "Elegir espacio de carga",
                "El archivo contiene varios espacios:",
                names,
                0,
                False,
            )
            if not accepted:
                return
            chosen = next(space for space in result.spaces if space.name == name)

        self.loading_space_form_panel.set_loading_space(chosen)
        self.statusBar().showMessage(
            f"Espacio de carga '{chosen.name}' aplicado desde '{path.name}'.", _STATUS_MESSAGE_MS
        )

    def _on_import_loading_space_excel(self) -> None:
        path = self._prompt_open_excel_path("Importar espacio de carga desde Excel")
        if path is None:
            return
        self._import_loading_spaces_from_path(path)

    # ------------------------------------------------------------------
    # Catálogo de productos y perfiles de espacio (fase 7.1)
    # ------------------------------------------------------------------

    def _apply_catalog_availability(self) -> None:
        """Deshabilita las acciones de catálogo/perfiles cuando la base no está disponible."""
        available = self._catalog_service is not None
        for action in (
            self.action_open_catalog,
            self.action_add_from_catalog,
            self.action_save_product_to_catalog,
            self.action_predefined_profiles,
            self.action_save_as_profile,
            self.action_import_catalog_excel,
            self.action_import_catalog_excel_mapping,
            self.action_bulk_import_catalog_excel,
            self.action_export_catalog_excel,
            self.action_import_packing_list_excel,
        ):
            action.setEnabled(available)

    def _on_open_catalog(self) -> None:
        if self._catalog_service is None:
            return
        dialog = ProductCatalogDialog(
            self,
            repository=self._catalog_service.products,
            on_excel_dropped=lambda path: self._on_catalog_dialog_excel_dropped(path, dialog),
        )
        if dialog.exec() != ProductCatalogDialog.DialogCode.Accepted:
            return
        chosen = dialog.selected_units_to_add()
        if not chosen:
            return

        existing_skus = {unit.sku.lower() for unit in self.product_table_panel.model.load_units()}
        to_add = []
        skipped: list[str] = []
        for catalog_unit in chosen:
            if catalog_unit.sku.lower() in existing_skus:
                skipped.append(catalog_unit.sku)
                continue
            to_add.append(CatalogService.copy_to_project(catalog_unit))
            existing_skus.add(catalog_unit.sku.lower())

        if to_add:
            self.product_table_panel.model.add_units(to_add)
            self.statusBar().showMessage(
                f"{len(to_add)} producto(s) añadido(s) desde el catálogo.", _STATUS_MESSAGE_MS
            )
        if skipped:
            self._show_warning(
                "SKU ya presente en el proyecto",
                "No se añadieron los siguientes productos porque su SKU ya existe en "
                "el proyecto actual: " + ", ".join(skipped),
            )

    def _on_save_product_to_catalog(self) -> None:
        if self._catalog_service is None:
            return
        indexes = self.product_table_panel.table_view.selectionModel().selectedRows()
        if not indexes:
            self._show_warning(
                "Sin selección", "Selecciona un producto de la tabla para guardarlo en el catálogo."
            )
            return
        unit = self.product_table_panel.model.load_units()[indexes[0].row()]

        existing = self._catalog_service.products.get_by_sku(unit.sku)
        if existing is None:
            try:
                self._catalog_service.products.add(unit)
            except RepositoryError as exc:
                self._show_warning("No se pudo guardar en el catálogo", str(exc))
                return
            self.statusBar().showMessage(
                f"Producto '{unit.sku}' guardado en el catálogo.", _STATUS_MESSAGE_MS
            )
            return

        response = QMessageBox.question(
            self,
            "El SKU ya existe en el catálogo",
            f"Ya existe un producto de catálogo con SKU '{unit.sku}'. ¿Qué deseas hacer?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.SaveAll
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return
        if response == QMessageBox.StandardButton.Save:
            try:
                self._catalog_service.products.update(replace(unit, id=existing.id))
            except RepositoryError as exc:
                self._show_warning("No se pudo actualizar el catálogo", str(exc))
                return
            self.statusBar().showMessage(
                f"Producto '{unit.sku}' actualizado en el catálogo.", _STATUS_MESSAGE_MS
            )
            return

        # SaveAll se reutiliza aquí como "Guardar con otro SKU".
        new_sku, accepted = QInputDialog.getText(
            self, "Guardar con otro SKU", "Nuevo SKU para el catálogo:", text=f"{unit.sku}-2"
        )
        if not accepted or not new_sku.strip():
            return
        try:
            self._catalog_service.products.add(replace(unit, id=uuid4(), sku=new_sku.strip()))
        except RepositoryError as exc:
            self._show_warning("No se pudo guardar en el catálogo", str(exc))
            return
        self.statusBar().showMessage(
            f"Producto guardado en el catálogo con SKU '{new_sku.strip()}'.", _STATUS_MESSAGE_MS
        )

    def _on_open_profiles(self) -> None:
        if self._catalog_service is None:
            return
        dialog = LoadingSpaceProfilesDialog(self, repository=self._catalog_service.profiles)
        if dialog.exec() != LoadingSpaceProfilesDialog.DialogCode.Accepted:
            return
        chosen = dialog.result_space()
        if chosen is None:
            return
        self.loading_space_form_panel.set_loading_space(
            CatalogService.copy_profile_to_project(chosen)
        )
        self.statusBar().showMessage(f"Perfil '{chosen.name}' aplicado.", _STATUS_MESSAGE_MS)

    def _on_save_as_profile(self) -> None:
        if self._catalog_service is None:
            return
        space = self.loading_space_form_panel.build_loading_space()
        if space is None:
            self._show_warning(
                "Espacio de carga incompleto",
                "Define un espacio de carga válido antes de guardarlo como perfil.",
            )
            return

        existing = self._catalog_service.profiles.get_by_name(space.name)
        if existing is None:
            try:
                self._catalog_service.profiles.add(space)
            except RepositoryError as exc:
                self._show_warning("No se pudo guardar el perfil", str(exc))
                return
            self.statusBar().showMessage(f"Perfil '{space.name}' guardado.", _STATUS_MESSAGE_MS)
            return

        response = QMessageBox.question(
            self,
            "El perfil ya existe",
            f"Ya existe un perfil llamado '{space.name}'. ¿Qué deseas hacer?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.SaveAll
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return
        if response == QMessageBox.StandardButton.Save:
            try:
                self._catalog_service.profiles.update(replace(space, id=existing.id))
            except RepositoryError as exc:
                self._show_warning("No se pudo actualizar el perfil", str(exc))
                return
            self.statusBar().showMessage(f"Perfil '{space.name}' actualizado.", _STATUS_MESSAGE_MS)
            return

        # SaveAll se reutiliza aquí como "Duplicar con otro nombre".
        new_name, accepted = QInputDialog.getText(
            self, "Guardar con otro nombre", "Nuevo nombre del perfil:", text=f"{space.name} (2)"
        )
        if not accepted or not new_name.strip():
            return
        try:
            self._catalog_service.profiles.add(replace(space, id=uuid4(), name=new_name.strip()))
        except RepositoryError as exc:
            self._show_warning("No se pudo guardar el perfil", str(exc))
            return
        self.statusBar().showMessage(
            f"Perfil guardado con el nombre '{new_name.strip()}'.", _STATUS_MESSAGE_MS
        )

    def _record_project_open_history(self, path: Path) -> None:
        if self._catalog_service is None:
            return
        try:
            self._catalog_service.project_history.record_open(
                project_id=self._current_project_id,
                project_name=path.stem,
                file_path=str(path),
                application_version=__version__,
            )
        except DatabaseError as exc:
            self.log_panel.append_entry(
                f"Aviso: no se pudo registrar el historial de apertura: {exc}"
            )

    def _record_project_save_history(self, path: Path) -> None:
        if self._catalog_service is None:
            return
        result = self._last_result
        try:
            self._catalog_service.project_history.record_save(
                project_id=self._current_project_id,
                project_name=path.stem,
                file_path=str(path),
                application_version=__version__,
                packed_count=result.packed_count if result is not None else None,
                requested_count=result.requested_count if result is not None else None,
                volume_utilization_percent=(
                    result.volume_utilization_percent if result is not None else None
                ),
                used_weight_kg=result.used_weight_kg if result is not None else None,
                algorithm_name=result.algorithm_name if result is not None else None,
            )
        except DatabaseError as exc:
            self.log_panel.append_entry(
                f"Aviso: no se pudo registrar el historial de guardado: {exc}"
            )

    def _record_run_history(self, result: PackingResult) -> None:
        if self._catalog_service is None:
            return
        try:
            self._catalog_service.run_history.record_run(
                project_id=self._current_project_id,
                project_name=self._project_display_name(),
                result=result,
                application_version=__version__,
                project_file_path=(
                    str(self._current_project_path)
                    if self._current_project_path is not None
                    else None
                ),
            )
        except DatabaseError as exc:
            self.log_panel.append_entry(
                f"Aviso: no se pudo registrar el historial de ejecución: {exc}"
            )

    def _rebuild_recent_projects_menu(self) -> None:
        self.menu_recent_projects.clear()
        existing = [p for p in self._settings.recent_project_files() if Path(p).is_file()]
        if len(existing) != len(self._settings.recent_project_files()):
            self._settings.set_recent_project_files(existing)

        if not existing:
            empty_action = self.menu_recent_projects.addAction("(sin proyectos recientes)")
            empty_action.setEnabled(False)
            return

        for file_path in existing:
            action = self.menu_recent_projects.addAction(Path(file_path).name)
            action.setToolTip(file_path)
            action.triggered.connect(
                lambda checked=False, p=file_path: self._on_open_recent_project(p)
            )
        self.menu_recent_projects.addSeparator()
        clear_action = self.menu_recent_projects.addAction("Limpiar lista")
        clear_action.triggered.connect(self._on_clear_recent_projects)

    def _on_open_recent_project(self, path_str: str) -> None:
        path = Path(path_str)
        if not path.is_file():
            self._show_warning("Archivo no encontrado", f"'{path}' ya no existe.")
            self._settings.set_recent_project_files(
                [p for p in self._settings.recent_project_files() if p != path_str]
            )
            return
        if not self._confirm_discard_unsaved_changes():
            return
        self._open_project_from_path(path)

    def _on_clear_recent_projects(self) -> None:
        self._settings.set_recent_project_files([])

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
        self._result_stale = False

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
        self._last_result = result
        self._result_stale = False
        self._populate_results(result)
        self.selection_details_panel.clear()
        self.viewer_widget.display_result(result, self._last_load_units_by_id)
        self._mark_dirty()
        self._set_state(STATE_FINISHED)
        if not self._cancel_requested:
            self._record_run_history(result)
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
        self.results_panel.set_stale(self._result_stale)

    def _set_running_controls_enabled(self, enabled: bool) -> None:
        for action in (
            self.action_run_optimization,
            self.action_new,
            self.action_open,
            self.action_new_product,
            self.action_delete_products,
            self.action_import,
            self.action_import_products,
            self.action_export,
            self.action_export_pdf,
            self.action_export_result_excel,
            self.action_import_loading_space_excel,
        ):
            action.setEnabled(enabled)
        if enabled:
            self._apply_catalog_availability()
        else:
            for action in (
                self.action_import_catalog_excel,
                self.action_import_catalog_excel_mapping,
                self.action_bulk_import_catalog_excel,
                self.action_export_catalog_excel,
                self.action_import_packing_list_excel,
            ):
                action.setEnabled(False)
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

    # ------------------------------------------------------------------
    # Ciclo de vida del proyecto (fase 7.0 — persistencia)
    # ------------------------------------------------------------------

    def _project_display_name(self) -> str:
        if self._current_project_path is not None:
            return self._current_project_path.stem
        return _UNTITLED_PROJECT_NAME

    def _update_window_title(self) -> None:
        marker = "*" if self._is_dirty else ""
        self.setWindowTitle(
            f"CargoOptimizer3D v{__version__} — {self._project_display_name()}{marker}"
        )
        if hasattr(self, "_project_status_label"):
            self._project_status_label.setText(f"{self._project_display_name()}{marker}")

    def _mark_dirty(self) -> None:
        if self._suspend_change_tracking:
            return
        self._is_dirty = True
        self._update_window_title()

    def _mark_clean(self) -> None:
        self._is_dirty = False
        self._update_window_title()

    def _on_project_data_changed(self, *_args: object) -> None:
        """Conectado a cambios de productos/espacio (fase 7.0).

        No existe todavía un panel de configuración de reglas de
        negocio (son fijas dentro de `rules`, sin controles de usuario
        en esta fase), así que solo productos y espacio pueden disparar
        esto — el mismo principio se aplicaría a un futuro panel de
        reglas sin cambiar esta lógica.
        """
        if self._suspend_change_tracking:
            return
        self._mark_dirty()
        if self._last_result is not None and not self._result_stale:
            self._result_stale = True
            self.results_panel.set_stale(True)
            self.log_panel.append_entry(_RESULT_INVALIDATED_MESSAGE)
            self.statusBar().showMessage(_RESULT_INVALIDATED_MESSAGE, _STATUS_MESSAGE_MS)

    def _confirm_discard_unsaved_changes(self) -> bool:
        """`True` si es seguro continuar (sin cambios, o el usuario ya decidió qué hacer)."""
        if not self._is_dirty:
            return True
        response = QMessageBox.question(
            self,
            "Cambios sin guardar",
            f"'{self._project_display_name()}' tiene cambios sin guardar. "
            "¿Deseas guardarlos antes de continuar?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return False
        if response == QMessageBox.StandardButton.Save:
            return self._on_save_project()
        return True

    def _collect_ui_state(self) -> dict[str, Any]:
        return {
            "theme": self._settings.theme(),
            "splitters": {
                _SPLITTER_MAIN: self._encode_bytes(self.main_splitter.saveState()),
                _SPLITTER_WORK_AREA: self._encode_bytes(self.work_area_splitter.saveState()),
                _SPLITTER_LEFT_WORK: self._encode_bytes(self.left_work_splitter.saveState()),
            },
            "docks_visible": {
                "projectTreeDock": self.project_tree_dock.isVisible(),
                "selectionDetailsDock": self.selection_details_dock.isVisible(),
            },
        }

    def _apply_ui_state(self, ui_state: Mapping[str, Any]) -> None:
        theme = ui_state.get("theme")
        if isinstance(theme, str) and theme in (THEME_LIGHT, THEME_DARK):
            self._set_theme(theme)

        splitters = ui_state.get("splitters")
        if isinstance(splitters, dict):
            self._restore_splitter_from_state(self.main_splitter, splitters.get(_SPLITTER_MAIN))
            self._restore_splitter_from_state(
                self.work_area_splitter, splitters.get(_SPLITTER_WORK_AREA)
            )
            self._restore_splitter_from_state(
                self.left_work_splitter, splitters.get(_SPLITTER_LEFT_WORK)
            )

        docks_visible = ui_state.get("docks_visible")
        if isinstance(docks_visible, dict):
            if "projectTreeDock" in docks_visible:
                self.project_tree_dock.setVisible(bool(docks_visible["projectTreeDock"]))
            if "selectionDetailsDock" in docks_visible:
                self.selection_details_dock.setVisible(bool(docks_visible["selectionDetailsDock"]))

    @staticmethod
    def _encode_bytes(value: QByteArray) -> str:
        return bytes(value.toBase64().data()).decode("ascii")

    @staticmethod
    def _restore_splitter_from_state(splitter: QSplitter, encoded: object) -> None:
        if not isinstance(encoded, str) or not encoded:
            return
        splitter.restoreState(QByteArray.fromBase64(encoded.encode("ascii")))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (nombre impuesto por Qt)
        if not self._confirm_discard_unsaved_changes():
            event.ignore()
            return
        worker = self._optimization_worker
        if worker is not None and worker.isRunning():
            worker.cancellation_token.cancel()
            worker.wait(5000)
        self._save_ui_state()
        self.viewer_widget.shutdown()
        if self._catalog_service is not None:
            self._catalog_service.close()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if has_excel_url(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        paths = all_excel_paths(event)
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        for path in paths:
            self._handle_dropped_excel_file(path)

    def _handle_dropped_excel_file(self, path: Path) -> None:
        """Detecta automáticamente el tipo de un `.xlsx` soltado y lo despacha (fase 8.1)."""
        try:
            kind = detect_template_kind(path)
        except ExcelError as exc:
            self._show_error("No se pudo leer el archivo Excel", str(exc))
            return

        if kind == "catalog":
            self._import_catalog_rows_into_project(path)
        elif kind == "packing_list":
            self._import_packing_list_from_path(path)
        elif kind == "loading_space":
            self._import_loading_spaces_from_path(path)
        else:
            self._handle_unrecognized_dropped_file(path)

    def _handle_unrecognized_dropped_file(self, path: Path) -> None:
        """Archivo soltado sin cabeceras oficiales: probar el mapeo por alias antes de rendirse."""
        headers = read_source_headers(path)
        mapping, _unrecognized = detect_column_mapping(headers, "catalog")
        if not mapping:
            self._show_warning(
                "Archivo no reconocido",
                f"'{path.name}' no coincide con ninguna plantilla oficial de CargoOptimizer3D "
                "ni se detectaron columnas conocidas de catálogo.",
            )
            return
        if self._catalog_service is None:
            self._show_warning(
                "Catálogo no disponible",
                "El mapeo de columnas requiere el catálogo, no disponible en modo limitado.",
            )
            return

        dialog = ColumnMappingDialog(
            self,
            target_kind="catalog",
            source_headers=headers,
            detected_mapping=mapping,
            profile_repository=self._catalog_service.import_mappings,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen_mapping = dialog.result_mapping() or {}
        result = import_catalog_with_mapping(path, chosen_mapping)

        existing_skus = {
            unit.sku.casefold() for unit in self.product_table_panel.model.load_units()
        }
        to_add = [unit for unit in result.units if unit.sku.casefold() not in existing_skus]
        if to_add:
            self.product_table_panel.model.add_units(to_add)
        self._report_import_outcome(
            path,
            imported_count=len(to_add),
            imported_label="producto(s) añadido(s) al proyecto (mapeo manual)",
            skipped_skus=[],
            row_errors=result.errors,
        )
