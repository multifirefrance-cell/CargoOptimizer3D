"""Jerarquía de excepciones de `infrastructure/excel/`.

Pequeña y plana, igual que `infrastructure/persistence` e
`infrastructure/database`: cada tipo indica un fallo distinto y
conserva la excepción original como causa (`raise ... from exc`).
Ninguna función de este paquete deja pasar una excepción cruda de
`openpyxl`/`zipfile` sin traducir.
"""

from __future__ import annotations


class ExcelError(Exception):
    """Base de todos los errores de `infrastructure/excel/`."""


class ExcelFileError(ExcelError):
    """El archivo no se pudo abrir: no es un `.xlsx` válido o está corrupto."""


class ExcelTemplateError(ExcelError):
    """El archivo se abrió pero no coincide con ninguna plantilla reconocida.

    Cabeceras faltantes, en otro orden, o una hoja completamente vacía.
    """
