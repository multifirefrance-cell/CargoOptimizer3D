"""Capa de presentación de CargoOptimizer3D.

Agrupa cualquier mecanismo de entrega del sistema al usuario o a otro
sistema: aplicación de escritorio (``presentation.desktop``, PySide6),
y en el futuro API REST (``presentation.api``) o interfaz web. Ninguna
regla de negocio, cálculo geométrico ni de optimización vive aquí: toda
esa lógica pertenece a ``cargo_optimizer.domain`` y
``cargo_optimizer.application``.

Regla de dependencia: puede depender de ``application`` (y
transitivamente de ``domain``). Puede depender de ``infrastructure``
únicamente en su código de composición/arranque (p. ej. para elegir qué
adaptador concreto inyectar), nunca la lógica de negocio.
"""
