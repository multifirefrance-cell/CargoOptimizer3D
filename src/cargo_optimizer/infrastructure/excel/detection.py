"""Detección de qué plantilla oficial coincide con un `.xlsx` dado, por sus cabeceras.

Usado por la acción genérica "Archivo > Importar Excel" de
`MainWindow`, que no sabe de antemano si el archivo elegido es un
catálogo, un packing list o un perfil de espacio de carga.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from cargo_optimizer.infrastructure.excel.loading_space_rows import LOADING_SPACE_COLUMNS
from cargo_optimizer.infrastructure.excel.packing_list_importer import PACKING_LIST_COLUMNS
from cargo_optimizer.infrastructure.excel.product_rows import PRODUCT_COLUMNS
from cargo_optimizer.infrastructure.excel.workbook_utils import get_active_worksheet, open_workbook

TemplateKind = Literal["catalog", "packing_list", "loading_space"]

_KNOWN_SCHEMAS: tuple[tuple[TemplateKind, tuple[str, ...]], ...] = (
    ("catalog", PRODUCT_COLUMNS),
    ("packing_list", PACKING_LIST_COLUMNS),
    ("loading_space", LOADING_SPACE_COLUMNS),
)


def detect_template_kind(path: Path) -> TemplateKind | None:
    """Identifica la plantilla oficial que coincide con las cabeceras del archivo.

    Devuelve ``None`` si el archivo abre correctamente pero no coincide
    con ninguna cabecera conocida — nunca adivina, deja que quien llama
    decida cómo informar al usuario. Puede lanzar `ExcelFileError` si el
    archivo está corrupto o no es un `.xlsx` válido.
    """
    workbook = open_workbook(path)
    worksheet = get_active_worksheet(workbook)
    for kind, columns in _KNOWN_SCHEMAS:
        header = tuple(
            (
                ""
                if worksheet.cell(row=1, column=i).value is None
                else str(worksheet.cell(row=1, column=i).value).strip().casefold()
            )
            for i in range(1, len(columns) + 1)
        )
        expected = tuple(column.casefold() for column in columns)
        if header == expected:
            return kind
    return None
