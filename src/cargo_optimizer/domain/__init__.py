"""Dominio de CargoOptimizer3D.

Contiene las entidades y reglas de negocio puras del sistema: Loading
Space, Load Unit y sus invariantes. Es el núcleo del SDK.

Regla de dependencia (no negociable): este paquete no importa nada de
``application``, ``infrastructure`` ni ``presentation``, ni de ninguna
biblioteca externa de UI, persistencia, ofimática o visualización
(PySide6/Qt, SQLAlchemy, openpyxl, ReportLab, VTK). Es la capa más
interna: todo lo demás depende de ella, ella no depende de nada. Esta
regla se verifica automáticamente con import-linter (ver
``pyproject.toml`` y ``docs/ADR/ADR-0004``).
"""
