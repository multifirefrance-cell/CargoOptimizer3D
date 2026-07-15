"""Expansión de LoadUnit (con quantity) en instancias físicas individuales."""

from __future__ import annotations

from collections.abc import Sequence

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.optimization.models import PhysicalLoadInstance


def expand_load_units(load_units: Sequence[LoadUnit]) -> tuple[PhysicalLoadInstance, ...]:
    """Convierte cada `LoadUnit` en `quantity` `PhysicalLoadInstance`, en orden estable.

    Una caja grupal con `units_per_package > 1` sigue siendo una sola
    instancia geométrica por unidad de `quantity`: `units_per_package`
    nunca se expande aquí (los extintores dentro de una caja grupal no
    son objetos geométricos independientes). No modifica ningún
    `LoadUnit`. `source_order` crece de forma estrictamente monótona a
    través de todos los `load_units`, no solo dentro de cada uno, para
    que el orden de entrada completo quede preservado como desempate
    determinista final.
    """
    instances: list[PhysicalLoadInstance] = []
    source_order = 0
    for load_unit in load_units:
        for instance_number in range(1, load_unit.quantity + 1):
            instances.append(PhysicalLoadInstance(load_unit, instance_number, source_order))
            source_order += 1
    return tuple(instances)
