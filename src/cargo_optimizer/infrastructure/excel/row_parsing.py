"""Ayudas genéricas de conversión fila -> valor, compartidas por todos los esquemas de columnas.

`product_rows.py` (catálogo) y `loading_space_rows.py` (perfiles de
espacio) necesitan exactamente la misma lógica de parseo (celda en
blanco, booleano en español, número, etiqueta de enum): vive aquí una
sola vez en lugar de duplicarse en cada esquema.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_TRUE_LABELS = frozenset({"si", "sí", "true", "1", "yes", "x"})
_FALSE_LABELS = frozenset({"no", "false", "0"})


class RowConversionError(Exception):
    """Error de conversión de una única fila (capturado siempre por el importador)."""

    def __init__(self, row_number: int, message: str) -> None:
        super().__init__(message)
        self.row_number = row_number
        self.message = message


def is_blank(raw: object) -> bool:
    return raw is None or str(raw).strip() == ""


def parse_enum_label(
    mapping: Mapping[Any, str], raw: object, *, field_name: str, row_number: int
) -> Any:
    """Acepta tanto la etiqueta en español como el valor interno estable del enum."""
    text = "" if raw is None else str(raw).strip()
    normalized = text.casefold()
    for enum_value, label in mapping.items():
        if normalized == label.casefold() or normalized == str(enum_value).casefold():
            return enum_value
    valid = ", ".join(sorted(mapping.values()))
    raise RowConversionError(
        row_number, f"'{field_name}' inválido: '{text}'. Valores válidos: {valid}."
    )


def parse_bool(raw: object, *, field_name: str, row_number: int, default: bool) -> bool:
    if is_blank(raw):
        return default
    text = str(raw).strip().casefold()
    if text in _TRUE_LABELS:
        return True
    if text in _FALSE_LABELS:
        return False
    raise RowConversionError(row_number, f"'{field_name}' inválido: '{raw}'. Usa 'Si' o 'No'.")


def format_bool(value: bool) -> str:
    return "Si" if value else "No"


def parse_required_float(raw: object, *, field_name: str, row_number: int) -> float:
    if is_blank(raw):
        raise RowConversionError(row_number, f"'{field_name}' no puede estar vacío.")
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise RowConversionError(row_number, f"'{field_name}' debe ser numérico: '{raw}'.") from exc


def parse_optional_float(raw: object, *, field_name: str, row_number: int) -> float | None:
    if is_blank(raw):
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise RowConversionError(row_number, f"'{field_name}' debe ser numérico: '{raw}'.") from exc


def parse_int(raw: object, *, field_name: str, row_number: int, default: int) -> int:
    if is_blank(raw):
        return default
    try:
        return int(float(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise RowConversionError(
            row_number, f"'{field_name}' debe ser un número entero: '{raw}'."
        ) from exc
