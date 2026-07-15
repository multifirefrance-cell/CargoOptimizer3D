"""Modelos Qt (`QAbstractItemModel` y variantes) de `presentation/desktop`.

Envuelven entidades de `cargo_optimizer.domain` (inmutables): una
edición reconstruye la entidad completa con `dataclasses.replace` y la
sustituye en la lista respaldada por el modelo, nunca muta el `LoadUnit`
existente. Ningún modelo aquí conoce `PackingEngine`: solo presentan y
editan datos de dominio, la ejecución del motor es de una fase futura.
"""
