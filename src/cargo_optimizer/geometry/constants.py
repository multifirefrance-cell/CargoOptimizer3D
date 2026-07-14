"""Constantes geométricas compartidas por todo el motor geométrico."""

from __future__ import annotations

GEOMETRY_EPSILON_CM: float = 1e-9
"""Tolerancia única para comparaciones de punto flotante, en centímetros.

Dos coordenadas o extensiones que difieran menos que este valor se
consideran iguales a efectos de contención, contacto, colisión y
soporte. El valor (1e-9 cm) es muchísimo menor que cualquier
tolerancia de fabricación o medición real, por lo que absorbe errores
de redondeo de coma flotante sin introducir imprecisión perceptible.

Toda comparación geométrica sensible en este paquete debe usar esta
constante; no se dispersan números mágicos por el código.
"""
