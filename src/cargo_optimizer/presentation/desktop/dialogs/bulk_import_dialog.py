"""`BulkImportDialog`: importar varios archivos Excel uno tras otro (fase 8.1, sección 8).

Recibe un `Callable[[Path], ImportReport]` inyectado desde
`MainWindow` (la misma función que ya conecta mapeo automático,
resolución de duplicados por defecto y escritura transaccional en el
catálogo para un único archivo) — este diálogo solo orquesta la lista
de archivos y muestra el resumen final, nunca importa nada él mismo.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cargo_optimizer.infrastructure.excel.exceptions import ExcelError
from cargo_optimizer.infrastructure.excel.import_report import (
    BulkImportReport,
    ImportReport,
    export_import_report,
)
from cargo_optimizer.infrastructure.excel.results import RowError

_SUMMARY_COLUMNS = (
    "Archivo",
    "Filas leídas",
    "Importadas",
    "Actualizadas",
    "Duplicadas",
    "Ignoradas",
    "Errores",
)


class BulkImportDialog(QDialog):
    """Diálogo modal: selecciona varios archivos Excel, los importa y muestra el resumen final."""

    def __init__(
        self, parent: QWidget | None, *, import_one: Callable[[Path], ImportReport]
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Importación masiva")
        self.resize(640, 480)
        self._import_one = import_one
        self._selected_paths: list[Path] = []
        self._reports: list[ImportReport] = []

        self._file_list = QListWidget(self)
        self._choose_button = QPushButton("Seleccionar archivos…", self)
        self._choose_button.clicked.connect(self._on_choose_files)
        self._import_button = QPushButton("Importar todos", self)
        self._import_button.setProperty("class", "primary")
        self._import_button.clicked.connect(self._on_import_all)
        self._import_button.setEnabled(False)

        self._summary_table = QTableWidget(0, len(_SUMMARY_COLUMNS), self)
        self._summary_table.setHorizontalHeaderLabels(list(_SUMMARY_COLUMNS))
        self._summary_table.setAlternatingRowColors(False)
        self._summary_table.verticalHeader().setVisible(False)
        _sh = self._summary_table.horizontalHeader()
        _sh.setStretchLastSection(False)
        _sh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for _col in range(1, len(_SUMMARY_COLUMNS)):
            _sh.setSectionResizeMode(_col, QHeaderView.ResizeMode.Interactive)
            _sh.resizeSection(_col, 85)

        self._save_report_button = QPushButton("Guardar informe como Excel…", self)
        self._save_report_button.clicked.connect(self._on_save_report)
        self._save_report_button.setEnabled(False)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        close_box.rejected.connect(self.reject)

        top_row = QHBoxLayout()
        top_row.addWidget(self._choose_button)
        top_row.addWidget(self._import_button)
        top_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self._file_list)
        layout.addWidget(QLabel("Resumen final:", self))
        layout.addWidget(self._summary_table)
        layout.addWidget(self._save_report_button)
        layout.addWidget(close_box)

    def _on_choose_files(self) -> None:
        paths_str, _selected_filter = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivos Excel", "", "Archivos Excel (*.xlsx)"
        )
        if not paths_str:
            return
        self._selected_paths = [Path(p) for p in paths_str]
        self._file_list.clear()
        self._file_list.addItems([path.name for path in self._selected_paths])
        self._import_button.setEnabled(True)

    def _on_import_all(self) -> None:
        self._reports = []
        for path in self._selected_paths:
            try:
                report = self._import_one(path)
            except ExcelError as exc:
                report = ImportReport(
                    source_name=path.name,
                    rows_read=0,
                    imported_count=0,
                    updated_count=0,
                    duplicate_count=0,
                    ignored_count=0,
                    errors=(RowError(row_number=0, message=str(exc)),),
                    elapsed_seconds=0.0,
                )
                QMessageBox.warning(self, "No se pudo importar", f"'{path.name}': {exc}")
            self._reports.append(report)
        self._populate_summary()
        self._save_report_button.setEnabled(bool(self._reports))

    def _populate_summary(self) -> None:
        self._summary_table.setRowCount(len(self._reports))
        for row, report in enumerate(self._reports):
            values = (
                report.source_name,
                report.rows_read,
                report.imported_count,
                report.updated_count,
                report.duplicate_count,
                report.ignored_count,
                report.error_count,
            )
            for column, value in enumerate(values):
                self._summary_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _on_save_report(self) -> None:
        path_str, _selected_filter = QFileDialog.getSaveFileName(
            self, "Guardar informe", "Informe_importacion.xlsx", "Archivos Excel (*.xlsx)"
        )
        if not path_str:
            return
        path = Path(path_str)
        if path.suffix.casefold() != ".xlsx":
            path = path.with_suffix(".xlsx")
        export_import_report(BulkImportReport(tuple(self._reports)), path)
        QMessageBox.information(self, "Informe guardado", f"Informe guardado en '{path.name}'.")

    def reports(self) -> tuple[ImportReport, ...]:
        """Los informes de cada archivo importado en esta sesión del diálogo."""
        return tuple(self._reports)
