"""Núcleo (SDK) de CargoOptimizer3D.

Este paquete contiene toda la lógica de dominio y negocio: modelos de
Loading Space y Load Unit, motor geométrico, motor de restricciones y
motor de optimización.

Regla de arquitectura: este paquete no puede importar nada de
``cargo_optimizer.ui`` ni de ninguna biblioteca de interfaz gráfica
(PySide6, Qt). Debe ser utilizable desde una API REST, un ERP o un
script de línea de comandos sin ninguna dependencia de UI.
"""
