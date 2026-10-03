"""`SceneBuilder`: transforma un `PackingResult` ya calculado en un `SceneModel`.

Función pura respecto a sus entradas (mismo `PackingResult` +
`load_units_by_id` -> mismo `SceneModel`): no importa PyVista, VTK ni
Qt, así que se prueba sin GPU ni `QApplication`. No decide dónde
colocar nada (eso ya está decidido, viene en `result`), no reevalúa
ninguna regla de `rules`, no modifica `domain`.

Asignación de colores (fase EasyCargo): `ColorRegistry.assign_unique_palette_colors`
garantiza que nunca dos SKUs distintos reciban el mismo color de paleta,
incluso si sus hashes de crc32 colisionan. La asignación se hace una
sola vez por llamada a `build()` (no por caja), así que cada SKU tiene
exactamente un color en toda la escena.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from cargo_optimizer.domain.load_unit import LoadUnit
from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.domain.placement import Placement
from cargo_optimizer.presentation.desktop.viewer.color_registry import ColorRegistry
from cargo_optimizer.presentation.desktop.viewer.models import PlacementVisualModel, SceneModel

_UNKNOWN_SKU = "?"
_UNKNOWN_NAME = "Desconocido"
_UNKNOWN_PACKAGE_TYPE = "?"


class SceneBuilder:
    """Construye un `SceneModel` a partir de un `PackingResult` y el catálogo de `LoadUnit`."""

    def __init__(self, color_registry: ColorRegistry | None = None) -> None:
        self._color_registry = color_registry or ColorRegistry()

    def build(self, result: PackingResult, load_units_by_id: Mapping[UUID, LoadUnit]) -> SceneModel:
        # 1. Recolectar todos los SKUs únicos y sus colores declarados
        sku_color_map: dict[str, str | None] = {}
        unit_by_id: dict[UUID, LoadUnit] = {}
        for placement in result.placements:
            lu = load_units_by_id.get(placement.load_unit_id)
            if lu is not None:
                sku_color_map[lu.sku] = lu.color_hex
                unit_by_id[placement.load_unit_id] = lu
            else:
                # Unidad desconocida: clave = UUID como string para la paleta
                sku_color_map[str(placement.load_unit_id)] = None

        # 2. Asignación global y sin colisiones: 1 color por SKU
        color_by_sku = self._color_registry.assign_unique_palette_colors(sku_color_map)

        # 3. Construir los visuales usando el color ya resuelto
        visuals: list[PlacementVisualModel] = []
        for placement in result.placements:
            lu = unit_by_id.get(placement.load_unit_id)
            sku = lu.sku if lu is not None else str(placement.load_unit_id)
            color_hex = color_by_sku.get(sku, "#808080")
            visual = self._build_placement_visual(placement, lu, color_hex)
            visuals.append(visual)

        return SceneModel(
            loading_space=result.loading_space,
            placement_visuals=tuple(visuals),
            color_mapping=color_by_sku,
        )

    def _build_placement_visual(
        self,
        placement: Placement,
        load_unit: LoadUnit | None,
        color_hex: str,
    ) -> PlacementVisualModel:
        if load_unit is not None:
            return PlacementVisualModel(
                sequence_number=placement.sequence_number,
                instance_number=placement.instance_number,
                load_unit_id=placement.load_unit_id,
                sku=load_unit.sku,
                name=load_unit.name,
                position=(placement.x_cm, placement.y_cm, placement.z_cm),
                oriented_dimensions=(
                    placement.length_cm,
                    placement.width_cm,
                    placement.height_cm,
                ),
                orientation_code=placement.orientation.code.value,
                weight_kg=load_unit.weight_kg,
                package_type=load_unit.package_type.value,
                units_per_package=load_unit.units_per_package,
                is_extinguisher=load_unit.is_extinguisher,
                extinguisher_nominal_kg=load_unit.extinguisher_nominal_kg,
                fragile=load_unit.fragile,
                max_stack_count=load_unit.max_stack_count,
                notes=load_unit.notes,
                color_hex=color_hex,
            )

        # LoadUnit desconocida (dato inconsistente): visual genérico con
        # valores de repuesto, nunca una excepción — ver ADR-0011.
        return PlacementVisualModel(
            sequence_number=placement.sequence_number,
            instance_number=placement.instance_number,
            load_unit_id=placement.load_unit_id,
            sku=_UNKNOWN_SKU,
            name=_UNKNOWN_NAME,
            position=(placement.x_cm, placement.y_cm, placement.z_cm),
            oriented_dimensions=(placement.length_cm, placement.width_cm, placement.height_cm),
            orientation_code=placement.orientation.code.value,
            weight_kg=0.0,
            package_type=_UNKNOWN_PACKAGE_TYPE,
            units_per_package=1,
            is_extinguisher=False,
            extinguisher_nominal_kg=None,
            fragile=False,
            max_stack_count=1,
            notes="",
            color_hex=color_hex,
        )
