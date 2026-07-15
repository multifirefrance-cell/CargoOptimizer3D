"""Modelo visual del visor 3D — dataclasses propias de `presentation`.

Proyección de solo lectura para `SceneController`, construida por
`SceneBuilder.build(...)`. No sustituyen a `PackingResult`/`Placement`/
`LoadUnit`: `SceneModel.loading_space` referencia el `LoadingSpace` real
del `PackingResult` (dato inmutable, seguro de reutilizar tal cual, sin
copiar sus campos), y `PlacementVisualModel` es la traducción de cada
`Placement` a lo que hace falta para dibujarlo, nada más.

`instance_number` se añade al listado de campos del encargo de la fase
6.1 (que no lo incluía) porque la propia sección 13 del encargo pide
mostrar "instancia" y "secuencia de carga" como datos separados en
`SelectionDetailsPanel` — son conceptos distintos en `Placement`
(`instance_number`: cuál de las N unidades físicas solicitadas es esta;
`sequence_number`: en qué orden la colocó el algoritmo, ver
`docs/DomainModel.md`). Omitir el campo habría mostrado el mismo número
bajo dos etiquetas distintas, un dato engañoso, no solo una omisión
estética.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from cargo_optimizer.domain.loading_space import LoadingSpace


@dataclass(frozen=True, slots=True)
class PlacementVisualModel:
    """Todo lo que `SceneController`/`SelectionDetailsPanel` necesitan de un `Placement`."""

    sequence_number: int
    instance_number: int
    load_unit_id: UUID
    sku: str
    name: str
    position: tuple[float, float, float]
    oriented_dimensions: tuple[float, float, float]
    orientation_code: str
    weight_kg: float
    package_type: str
    units_per_package: int
    is_extinguisher: bool
    extinguisher_nominal_kg: float | None
    fragile: bool
    max_stack_count: int
    notes: str
    color_hex: str
    visible: bool = True
    selected: bool = False


@dataclass(frozen=True, slots=True)
class SceneModel:
    """Todo lo que `SceneController` necesita para (re)construir la escena 3D."""

    loading_space: LoadingSpace
    placement_visuals: tuple[PlacementVisualModel, ...]
    selected_sequence_number: int | None = None
    container_visible: bool = True
    boxes_visible: bool = True
    axes_visible: bool = True
    color_mapping: dict[str, str] = field(default_factory=dict)
