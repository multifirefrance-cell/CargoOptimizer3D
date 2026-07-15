"""Ayudas compartidas para arrastrar y soltar archivos `.xlsx` (fase 8.1).

Usado por `MainWindow` y por `ProductCatalogDialog` — ambos aceptan
soltar un Excel directamente sobre la ventana; esta lógica de
detección (¿el `QDropEvent` trae al menos una ruta `.xlsx` local?) es
idéntica en los dos sitios.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

_XLSX_SUFFIX = ".xlsx"


def _local_xlsx_paths(urls: list[QUrl]) -> list[Path]:
    paths: list[Path] = []
    for url in urls:
        local_path = url.toLocalFile()
        if local_path and local_path.casefold().endswith(_XLSX_SUFFIX):
            paths.append(Path(local_path))
    return paths


def has_excel_url(event: QDragEnterEvent) -> bool:
    """Verdadero si el evento de arrastre trae al menos un archivo `.xlsx` local."""
    mime_data = event.mimeData()
    return mime_data.hasUrls() and bool(_local_xlsx_paths(mime_data.urls()))


def first_excel_path(event: QDropEvent) -> Path | None:
    """La primera ruta `.xlsx` local del evento de soltar, o `None` si no hay ninguna."""
    mime_data = event.mimeData()
    if not mime_data.hasUrls():
        return None
    paths = _local_xlsx_paths(mime_data.urls())
    return paths[0] if paths else None


def all_excel_paths(event: QDropEvent) -> list[Path]:
    """Todas las rutas `.xlsx` locales del evento de soltar (para soltar varios archivos)."""
    mime_data = event.mimeData()
    if not mime_data.hasUrls():
        return []
    return _local_xlsx_paths(mime_data.urls())
