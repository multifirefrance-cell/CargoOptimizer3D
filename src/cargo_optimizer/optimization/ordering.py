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

# (group, volume_key, -max_dim, -weight, sku, instance_number, source_order)
# group: 0 = fondo-explícito (prio 1-49), 1 = auto, 2 = techo-explícito (prio 50-99)
OrderKey = tuple[int, float, float, float, str, int, int]


def order_instances(
    instances: Sequence[PhysicalLoadInstance],
    loading_space: LoadingSpace,
    rules_engine: RulesEngine,
) -> tuple[PhysicalLoadInstance, ...]:
    """Ordena las instancias para maximizar densidad y obtener bloques ordenados por SKU.

    Prioridad (menor valor = antes):

    0. **loading_priority** del SKU (cuando > 0 anula el orden automático):
       - 1–49: fondo del contenedor; 1 = absolutamente primero, 49 = justo antes del
         grupo automático. Se ordenan entre sí por prioridad ascendente.
       - 0: automático — por volumen total (comportamiento predeterminado).
       - 50–99: techo del contenedor; 50 = inmediatamente después del grupo automático,
         99 = absolutamente último. Se ordenan entre sí por prioridad ascendente.
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
        prio = unit.loading_priority
        if prio == 0:
            group = 1                                    # automático: por volumen
            volume_key = -total_volume_cache[unit.id]
        elif prio <= 49:
            group = 0                                    # fondo explícito (1 = primero)
            volume_key = float(prio)
        else:
            group = 2                                    # techo explícito (99 = último)
            volume_key = float(prio)
        return (
            group,
            volume_key,
            -max(unit.dimensions.as_tuple()),           # desempate: mayor dimensión unitaria
            -unit.weight_kg,                            # desempate: mayor peso unitario
            unit.sku,                                   # desempate estable entre SKUs iguales
            instance.instance_number,                  # orden natural dentro del mismo SKU
            instance.source_order,
        )

    return tuple(sorted(instances, key=sort_key))
