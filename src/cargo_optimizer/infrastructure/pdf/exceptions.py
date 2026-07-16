"""Excepciones tipadas de `infrastructure/pdf/`.

Mismo criterio que `infrastructure/excel/exceptions.py` (fase 8.0): un
fallo de generación de un informe nunca se propaga como una excepción
cruda de `reportlab` hasta la interfaz.
"""

from __future__ import annotations


class PdfError(Exception):
    """Error base de `infrastructure/pdf/`."""


class PdfConfigError(PdfError):
    """La configuración del informe (plantilla, empresa, cliente) es inválida."""


class PdfRenderError(PdfError):
    """El documento no se pudo generar (fallo de `reportlab` o de escritura de archivo)."""
