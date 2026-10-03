"""Importación y exportación profesional de Excel (`.xlsx`), fase 8.0.

Depende únicamente de `domain` (nunca de `optimization`, `presentation`
ni de PySide6/Qt) — mismo criterio que `infrastructure/persistence` e
`infrastructure/database`. Usa exclusivamente `openpyxl`: nunca
`pandas`, `xlrd` ni CSV como sustituto. Ver `docs/Excel.md` para el
detalle completo (esquema de columnas, plantillas oficiales, modo de
importación fila a fila, formato profesional de exportación) y
`docs/ExcelAutomation.md` para el mapeador de columnas, perfiles
reutilizables, vista previa, importación parcial/masiva, resolución de
duplicados e informe final (fase 8.1).
"""

from __future__ import annotations

from cargo_optimizer.infrastructure.excel.advanced_export import (
    SheetSelection,
    default_sheet_order,
    export_packing_result_advanced,
    is_sheet_empty,
)
from cargo_optimizer.infrastructure.excel.catalog_exporter import export_catalog
from cargo_optimizer.infrastructure.excel.catalog_importer import import_catalog
from cargo_optimizer.infrastructure.excel.detection import TemplateKind, detect_template_kind
from cargo_optimizer.infrastructure.excel.exceptions import (
    ExcelError,
    ExcelFileError,
    ExcelTemplateError,
)
from cargo_optimizer.infrastructure.excel.import_plan import (
    DuplicateResolution,
    ImportPlan,
    ImportSelectionMode,
    build_import_plan,
)
from cargo_optimizer.infrastructure.excel.import_preview import (
    CatalogImportPreview,
    build_catalog_preview,
)
from cargo_optimizer.infrastructure.excel.import_report import (
    BulkImportReport,
    ImportReport,
    build_import_report,
    export_import_report,
)
from cargo_optimizer.infrastructure.excel.loading_space_importer import import_loading_spaces
from cargo_optimizer.infrastructure.excel.mapping import (
    canonical_columns_for,
    detect_column_mapping,
    import_catalog_with_mapping,
    import_loading_spaces_with_mapping,
    import_packing_list_with_mapping,
    read_source_headers,
)
from cargo_optimizer.infrastructure.excel.packing_list_importer import import_packing_list
from cargo_optimizer.infrastructure.excel.product_rows import CATALOG_SHEET_NAME, PRODUCT_COLUMNS
from cargo_optimizer.infrastructure.excel.result_exporter import (
    export_packing_result,
    export_packing_result_csv,
)
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
    PRODUCT_IMPORT_TEMPLATE_FILENAME,
    generate_all_templates,
    generate_catalog_template,
    generate_loading_space_template,
    generate_optimization_result_template,
    generate_packing_list_template,
    generate_product_import_template,
)

__all__ = [
    "CATALOG_SHEET_NAME",
    "CATALOG_TEMPLATE_FILENAME",
    "BulkImportReport",
    "CatalogImportPreview",
    "CatalogImportResult",
    "DuplicateResolution",
    "ExcelError",
    "ExcelFileError",
    "ExcelTemplateError",
    "ImportPlan",
    "ImportReport",
    "ImportSelectionMode",
    "LOADING_SPACE_TEMPLATE_FILENAME",
    "LoadingSpaceImportResult",
    "OPTIMIZATION_RESULT_TEMPLATE_FILENAME",
    "PACKING_LIST_TEMPLATE_FILENAME",
    "PRODUCT_COLUMNS",
    "PRODUCT_IMPORT_TEMPLATE_FILENAME",
    "PackingListImportResult",
    "RowConversionError",
    "RowError",
    "SheetSelection",
    "TemplateKind",
    "build_catalog_preview",
    "build_import_plan",
    "build_import_report",
    "canonical_columns_for",
    "default_sheet_order",
    "detect_column_mapping",
    "detect_template_kind",
    "export_catalog",
    "export_import_report",
    "export_packing_result",
    "export_packing_result_advanced",
    "export_packing_result_csv",
    "generate_all_templates",
    "generate_catalog_template",
    "generate_loading_space_template",
    "generate_optimization_result_template",
    "generate_packing_list_template",
    "generate_product_import_template",
    "import_catalog",
    "import_catalog_with_mapping",
    "import_loading_spaces",
    "import_loading_spaces_with_mapping",
    "import_packing_list",
    "import_packing_list_with_mapping",
    "is_sheet_empty",
    "read_source_headers",
]
