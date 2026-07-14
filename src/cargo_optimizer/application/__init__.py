"""Capa de aplicación de CargoOptimizer3D.

Contiene los casos de uso (orquestación) y los puertos: interfaces que
``infrastructure`` deberá implementar (repositorios de persistencia,
exportadores de Excel/PDF, proveedores de visualización). Esta capa
decide *qué* pasos ejecuta el sistema, nunca *cómo* se guarda o se
dibuja algo.

Regla de dependencia: depende únicamente de ``domain``. Nunca importa
``infrastructure`` ni ``presentation``.
"""
