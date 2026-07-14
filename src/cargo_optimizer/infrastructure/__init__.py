"""Capa de infraestructura de CargoOptimizer3D.

Contiene los adaptadores concretos que implementan los puertos
definidos en ``application``: persistencia (SQLAlchemy/SQLite, fase 7),
exportación a Excel (openpyxl, fase 8) y PDF (ReportLab, fase 8),
renderizado 3D (VTK, fase 5). Todavía no contiene ningún adaptador: se
irán añadiendo fase a fase.

Regla de dependencia: puede depender de ``application`` y ``domain``.
Nunca depende de ``presentation``.
"""
