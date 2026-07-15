"""Importación y exportación profesional de Excel (`.xlsx`), fase 8.0.

Depende únicamente de `domain` (nunca de `optimization`, `presentation`
ni de PySide6/Qt) — mismo criterio que `infrastructure/persistence` e
`infrastructure/database`. Usa exclusivamente `openpyxl`: nunca
`pandas`, `xlrd` ni CSV como sustituto. Ver `docs/Excel.md` para el
detalle completo (esquema de columnas, plantillas oficiales, modo de
importación fila a fila, formato profesional de exportación).
"""

from __future__ import annotations

from cargo_optimizer.infrastructure.excel.catalog_exporter import export_catalog
from cargo_optimizer.infrastructure.excel.catalog_importer import import_catalog
from cargo_optimizer.infrastructure.excel.detection import TemplateKind, detect_template_kind
from cargo_optimizer.infrastructure.excel.exceptions import (
    ExcelError,
    ExcelFileError,
    ExcelTemplateError,
)
from cargo_optimizer.infrastructure.excel.loading_space_importer import import_loading_spaces
from cargo_optimizer.infrastructure.excel.packing_list_importer import import_packing_list
from cargo_optimizer.infrastructure.excel.product_rows import CATALOG_SHEET_NAME, PRODUCT_COLUMNS
from cargo_optimizer.infrastructure.excel.result_exporter import export_packing_result
from cargo_optimizer.infrastructure.excel.results import (
    CatalogImportResult,
    LoadingSpaceImportResult,
    PackingListImportResult,
    RowError,
)
from cargo_optimizer.infrastructure.excel.row_parsing import RowConversionError
from cargo_optimizer.infrastructure.excel.templates import (
    CATALOG_TEMPLATE_FILENAME,
    LOADING_SPACE_TEMPLATE_FILENAME,
    OPTIMIZATION_RESULT_TEMPLATE_FILENAME,
    PACKING_LIST_TEMPLATE_FILENAME,
    generate_all_templates,
    generate_catalog_template,
    generate_loading_space_template,
    generate_optimization_result_template,
    generate_packing_list_template,
)

__all__ = [
    "CATALOG_SHEET_NAME",
    "CATALOG_TEMPLATE_FILENAME",
    "CatalogImportResult",
    "ExcelError",
    "ExcelFileError",
    "ExcelTemplateError",
    "LOADING_SPACE_TEMPLATE_FILENAME",
    "LoadingSpaceImportResult",
    "OPTIMIZATION_RESULT_TEMPLATE_FILENAME",
    "PACKING_LIST_TEMPLATE_FILENAME",
    "PRODUCT_COLUMNS",
    "PackingListImportResult",
    "RowConversionError",
    "RowError",
    "TemplateKind",
    "detect_template_kind",
    "export_catalog",
    "export_packing_result",
    "generate_all_templates",
    "generate_catalog_template",
    "generate_loading_space_template",
    "generate_optimization_result_template",
    "generate_packing_list_template",
    "import_catalog",
    "import_loading_spaces",
    "import_packing_list",
]
