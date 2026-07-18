"""Orden determinista de instancias para el algoritmo greedy.

Usa `RulesEngine` para determinar orientaciones válidas — nunca
reimplementa esa regla. El único hecho que no puede obtenerse de
`RulesEngine` (no es uno de sus métodos expuestos) es "es un extintor
individual grande", así que se importa directamente de
`cargo_optimizer.rules.extinguisher_rules`, evitando duplicar esa
comprobación en vez de reinventarla.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.models import PhysicalLoadInstance
from cargo_optimizer.rules.engine import RulesEngine
from cargo_optimizer.rules.extinguisher_rules import is_individual_large_extinguisher

OrderKey = tuple[int, int, int, float, float, float, str, int, int]


def order_instances(
    instances: Sequence[PhysicalLoadInstance],
    loading_space: LoadingSpace,
    rules_engine: RulesEngine,
) -> tuple[PhysicalLoadInstance, ...]:
    """Ordena las instancias según la prioridad, de mayor a menor:

    1. extintores individuales >= 3 kg nominales primero (colocarlos
       mientras el espacio bajo está libre, con independencia de su
       `max_stack_count` configurado);
    2. unidades con una sola orientación válida primero (más
       restringidas, más difíciles de encajar más tarde);
    3. unidades no apilables primero (`max_stack_count <= 1`);
    4. mayor volumen primero;
    5. mayor dimensión máxima primero;
    6. mayor peso primero;
    7. SKU ascendente (agrupación estable, cosmético);
    8. `instance_number` ascendente;
    9. `source_order` ascendente — desempate final, siempre presente.

    `orientation_count` se cachea por `load_unit.id` dentro de esta
    llamada: depende únicamente del `LoadUnit` y del `LoadingSpace`,
    nunca de la instancia física concreta, así que recalcularlo por
    cada instancia de una misma `LoadUnit` con `quantity` alta sería
    trabajo repetido innecesario. `max_stack_count` es un campo del
    propio `LoadUnit`, sin necesidad de caché.
    """
    orientation_count_cache: dict[UUID, int] = {}

    def sort_key(instance: PhysicalLoadInstance) -> OrderKey:
        unit = instance.load_unit
        if unit.id not in orientation_count_cache:
            orientation_count_cache[unit.id] = len(
                rules_engine.allowed_orientations(unit, loading_space)
            )

        orientation_count = orientation_count_cache[unit.id]

        return (
            0 if is_individual_large_extinguisher(unit) else 1,
            0 if orientation_count == 1 else 1,
            0 if unit.max_stack_count <= 1 else 1,
            -unit.dimensions.volume_cm3,
            -max(unit.dimensions.as_tuple()),
            -unit.weight_kg,
            unit.sku,
            instance.instance_number,
            instance.source_order,
        )

    return tuple(sorted(instances, key=sort_key))
