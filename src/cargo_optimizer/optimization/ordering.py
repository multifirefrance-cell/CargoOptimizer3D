"""Orden determinista de instancias para el algoritmo greedy.

Usa `RulesEngine` para determinar orientaciones válidas — nunca
reimplementa esa regla.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cargo_optimizer.domain.loading_space import LoadingSpace
from cargo_optimizer.optimization.models import PhysicalLoadInstance
from cargo_optimizer.rules.engine import RulesEngine

# (-total_volume, -max_dim, -weight, sku, instance_number, source_order)
OrderKey = tuple[float, float, float, str, int, int]


def order_instances(
    instances: Sequence[PhysicalLoadInstance],
    loading_space: LoadingSpace,
    rules_engine: RulesEngine,
) -> tuple[PhysicalLoadInstance, ...]:
    """Ordena las instancias para maximizar densidad y obtener bloques ordenados por SKU.

    Prioridad (menor valor = antes):

    1. Mayor **volumen total** del SKU primero (cantidad × volumen unitario) —
       el SKU con más unidades o piezas más grandes ocupa el fondo. Agrupa
       todas las instancias del mismo SKU consecutivamente, produciendo
       bloques/camas de un solo SKU en lugar de capas mezcladas y acelerando
       el cursor de patrón (OPT-17/19/20).
    2. Mayor dimensión máxima unitaria primero (desempate geométrico).
    3. Mayor peso unitario primero.
    4. SKU ascendente (desempate estable entre SKUs de igual volumen total).
    5. ``instance_number`` ascendente — orden natural dentro del mismo SKU.
    6. ``source_order`` ascendente (desempate final).
    """
    # Volumen total por SKU = n_instancias × volumen_unitario.
    total_volume_cache: dict[UUID, float] = {}
    for inst in instances:
        uid = inst.load_unit.id
        total_volume_cache[uid] = (
            total_volume_cache.get(uid, 0.0) + inst.load_unit.dimensions.volume_cm3
        )

    def sort_key(instance: PhysicalLoadInstance) -> OrderKey:
        unit = instance.load_unit
        return (
            -total_volume_cache[unit.id],           # mayor volumen total primero (fondo)
            -max(unit.dimensions.as_tuple()),       # desempate: mayor dimensión unitaria
            -unit.weight_kg,                        # desempate: mayor peso unitario
            unit.sku,                               # desempate estable entre SKUs iguales
            instance.instance_number,              # orden natural dentro del mismo SKU
            instance.source_order,
        )

    return tuple(sorted(instances, key=sort_key))
