"""Índice espacial de rejilla uniforme: fase *broad-phase* de colisión/soporte.

Separa la comprobación geométrica en dos fases, una técnica estándar de
detección de colisiones (no específica de este dominio):

- **Broad-phase** (este módulo): descarta barato, sin falsos negativos,
  la inmensa mayoría de cajas que con certeza NO pueden solaparse ni
  soportar a una caja candidata, devolviendo un superconjunto pequeño
  de posibles candidatas.
- **Narrow-phase** (sin cambios: `geometry.collision.boxes_overlap`,
  `geometry.support.horizontal_overlap_area_cm2`, etc.): decide la
  respuesta exacta, pero ahora solo sobre ese superconjunto pequeño, no
  sobre todos los `existing_placements` — el cuello de botella medido
  en `docs/OptimizerPerformance.md` (fases OPT-02, OPT-03→OPT-11).

`SpatialIndex` es puramente aditivo: nunca decide por sí mismo si dos
cajas colisionan o si una soporta a otra (eso lo sigue haciendo el
narrow-phase, sin ningún cambio). Solo reduce **cuántas** comparaciones
narrow-phase hacen falta. Si nunca se usa (parámetro `None` en todo el
código que lo consume), el comportamiento es exactamente el de antes.

## Garantía de "sin falsos negativos"

Cada caja se registra en todas las celdas de una rejilla uniforme
(`cell_size_cm`) que su extensión `[min, max]` toca en cada eje, con un
margen de seguridad (`_BOUNDARY_PADDING_CM`) mayor que cualquier deriva
de coma flotante realista, para que una caja cuyo borde caiga
exactamente sobre el límite de una celda no se registre solo en un
lado. Dos cajas cuyos intervalos reales se solapan (o se tocan) en los
tres ejes comparten, por construcción, al menos una celda — nunca al
revés: compartir una celda no implica solape real, solo indica "hay que
comprobarlo con el narrow-phase". `query_box` puede devolver
falsos positivos (cajas que en realidad no solapan ni soportan),
nunca falsos negativos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from cargo_optimizer.geometry.box import AxisAlignedBox

DEFAULT_CELL_SIZE_CM = 50.0
"""Tamaño de celda por defecto.

No se deriva de las dimensiones del Loading Space ni de las cajas
reales (mantiene `PackingState`/`SpatialIndex` construibles sin
argumentos, igual que antes de esta fase): 50 cm es un tamaño razonable
para los rangos típicos de Load Unit y Loading Space de este dominio
(decenas a cientos de cm) sin necesitar adaptarse dinámicamente. Una
celda peor calibrada solo cambia CUÁNTO filtra el broad-phase, nunca su
corrección.
"""

_BOUNDARY_PADDING_CM = 1e-6
"""Margen de seguridad al calcular en qué celdas registrar una caja.

Mucho mayor que `GEOMETRY_EPSILON_CM` (1e-9): absorbe con margen
cualquier deriva de coma flotante acumulada tras miles de sumas
(posiciones derivadas de sumar alturas de cajas ya colocadas), para que
una caja cuyo borde caiga por casualidad justo sobre un límite de celda
nunca quede registrada solo en un lado de esa frontera.
"""

_Cell = tuple[int, int, int]


def _cell_range(min_value: float, max_value: float, cell_size_cm: float) -> range:
    start = int((min_value - _BOUNDARY_PADDING_CM) // cell_size_cm)
    end = int((max_value + _BOUNDARY_PADDING_CM) // cell_size_cm)
    return range(start, end + 1)


@dataclass(slots=True)
class SpatialIndex:
    """Rejilla uniforme que indexa `AxisAlignedBox` por `sequence_number` de `Placement`.

    No conoce `Placement` ni `Sequence_number` como concepto de dominio:
    solo un identificador entero elegido por quien la usa
    (`optimization.state.PackingState` usa el `sequence_number` real,
    que ya es único y estable).
    """

    cell_size_cm: float = DEFAULT_CELL_SIZE_CM
    _cells: dict[_Cell, set[int]] = field(default_factory=lambda: defaultdict(set))

    def _cells_for_box(self, box: AxisAlignedBox) -> tuple[_Cell, ...]:
        xs = _cell_range(box.min_x, box.max_x, self.cell_size_cm)
        ys = _cell_range(box.min_y, box.max_y, self.cell_size_cm)
        zs = _cell_range(box.min_z, box.max_z, self.cell_size_cm)
        return tuple((x, y, z) for x in xs for y in ys for z in zs)

    def insert(self, identifier: int, box: AxisAlignedBox) -> None:
        """Registra `box` bajo `identifier` en todas las celdas que toca."""
        for cell in self._cells_for_box(box):
            self._cells[cell].add(identifier)

    def query_box(self, box: AxisAlignedBox) -> frozenset[int]:
        """Identificadores de cajas registradas que podrían solapar o tocar `box`.

        Superconjunto seguro (ver docstring del módulo): nunca omite un
        identificador cuya caja real solapa o toca `box`, puede incluir
        identificadores cuya caja real está más lejos de lo que sugiere
        compartir una celda (falso positivo, resuelto por el
        narrow-phase de quien llama).
        """
        result: set[int] = set()
        for cell in self._cells_for_box(box):
            candidates = self._cells.get(cell)
            if candidates:
                result.update(candidates)
        return frozenset(result)

    def query_point(self, x_cm: float, y_cm: float, z_cm: float) -> frozenset[int]:
        """Identificadores de cajas registradas cuya celda contiene el punto `(x, y, z)`.

        Mismo superconjunto seguro que `query_box`, para el caso
        degenerado de una consulta puntual (usado por
        `optimization.pruning` para "¿qué cajas podrían contener este
        punto candidato?" sin construir una `AxisAlignedBox` de tamaño
        cero).
        """
        result: set[int] = set()
        xs = _cell_range(x_cm, x_cm, self.cell_size_cm)
        ys = _cell_range(y_cm, y_cm, self.cell_size_cm)
        zs = _cell_range(z_cm, z_cm, self.cell_size_cm)
        for x in xs:
            for y in ys:
                for z in zs:
                    candidates = self._cells.get((x, y, z))
                    if candidates:
                        result.update(candidates)
        return frozenset(result)

    def __len__(self) -> int:
        """Número de celdas no vacías (diagnóstico/pruebas, no parte del contrato de consulta)."""
        return len(self._cells)
