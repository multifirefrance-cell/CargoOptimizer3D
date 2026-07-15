# Línea base de rendimiento — antes de la fase 4.2

Este documento registra el rendimiento **real, medido**, de
`GreedyExtremePointStrategy` tal como quedó al final de la fase 4.1,
antes de cualquier optimización de la fase 4.2. Es el punto de
comparación para juzgar si las optimizaciones de esta fase cumplen el
objetivo obligatorio (100 instancias, al menos 5x más rápido).

## Entorno de medición

- Python 3.12.10 (CPython, build de 64 bits).
- Windows 11, procesador Intel de arquitectura x86-64 (familia 6,
  modelo 154), un único hilo (el motor es secuencial, no paralelo).
- Sin ninguna dependencia externa instalada más allá de las ya
  declaradas en `pyproject.toml`.
- Mediciones tomadas con `time.perf_counter()` /
  `time.monotonic()` y memoria aproximada con `tracemalloc`
  (pico de memoria trazada, no RSS del proceso completo).

No se reportan rutas absolutas ni datos personales: todas las cifras
son de tiempo de ejecución y conteos, reproducibles con
`scripts/benchmark_optimizer.py` en cualquier máquina.

## Metodología

- Herramienta: `scripts/benchmark_optimizer.py` (nuevo en esta fase).
- Escenario determinista y mixto: 80 % cajas normales, 10 % extintor
  individual, 10 % caja grupal de extintores (ver
  `build_scenario()` en el script) — deliberadamente más realista que
  el escenario de SKU único usado como estimación en
  `docs/OptimizationEngine.md` al final de la fase 4.1.
- Tamaños: 10, 30, 60, 100 instancias, 3 repeticiones cada uno (mediana
  reportada); 100 instancias se corrió una sola vez por su duración.
- Además, perfilado real con `cProfile`/`pstats` sobre un escenario de
  60 instancias (mismo generador), analizado tanto por tiempo
  acumulado (`cumulative`) como por tiempo propio (`tottime`), para
  identificar los cuellos de botella reales y no supuestos.

## Resultados — benchmark end-to-end (antes de optimizar)

Escenario mixto (`build_scenario`), mediana de 3 repeticiones (100 con
una sola corrida):

| size | mediana (s) | min (s) | max (s) | packed | unpacked | candidatos generados | pico memoria (MB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10  | 0.196   | —       | —       | 10  | 0 | 865    | 0.18 |
| 100 | 102.635 | 102.635 | 102.635 | 100 | 0 | 79 405 | 1.20 |

Los tamaños 30 y 60 no se capturaron con el benchmark end-to-end antes
de empezar a optimizar (solo se perfilaron con `cProfile`, que añade su
propia sobrecarga y no es comparable a una medición de reloj limpia);
por eso no aparecen en esta tabla de referencia. La comparación real de
"antes/después" en `docs/OptimizerPerformance.md` se limita a los
tamaños 10 y 100, que sí tienen una medición limpia de referencia.

Adicionalmente, un benchmark independiente heredado de la fase 4.1
(escenario de SKU único, `tests/optimization/test_performance.py`
ejecutado manualmente fuera de los límites de la suite automática)
para **500 instancias** completó en segundo plano durante esta misma
sesión, sin que se le aplicara ninguna optimización todavía:

| size | tiempo (s) | tiempo aprox. |
|---:|---:|---:|
| 500 | 2465.75 | ~41 minutos |

Este dato de 500 confirma, con una cifra real y no extrapolada, la
magnitud del problema: un crecimiento marcadamente peor que lineal
(en línea con lo ya documentado en `docs/OptimizationEngine.md` como
"crecimiento cúbico").

## Perfilado real (cProfile, escenario mixto de 60 instancias)

Comando usado (biblioteca estándar únicamente, sin dependencias
nuevas):

```python
import cProfile, pstats
from scripts.benchmark_optimizer import build_scenario
from cargo_optimizer.optimization.engine import PackingEngine

request = build_scenario(60)
profiler = cProfile.Profile()
profiler.enable()
result = PackingEngine().optimize(request)
profiler.disable()
pstats.Stats(profiler).sort_stats("cumulative").print_stats(30)
pstats.Stats(profiler).sort_stats("tottime").print_stats(30)
```

Total: **98 435 465 llamadas de función en 23.641 s** para 60
instancias mixtas.

### Hallazgos principales, ordenados por impacto

1. **`optimization/scoring.py::bounding_dimensions`** (y su llamador
   `bounding_volume_increment_cm3`) — recalcula el `max(x)`, `max(y)`,
   `max(z)` de **todos** los placements aceptados hasta el momento, en
   **cada candidato evaluado**, no una vez por instancia. Para 60
   instancias generó 62 490 llamadas, 6.722 s acumulados solo en esta
   función; sumando las propiedades `Placement.max_x_cm` / `max_y_cm`
   / `max_z_cm` que invoca (~2.47 millones de llamadas cada una) y los
   `builtins.max`/`min` asociados, esta única pieza de código explica
   aproximadamente **el 40-50 % del tiempo total de ejecución**. Es
   además el hallazgo de mayor confianza: vive enteramente dentro de
   `optimization`, no toca `domain`, `geometry` ni `rules`, y el valor
   matemático que produce no cambia en absoluto si se calcula de forma
   incremental en vez de recorriendo todos los placements cada vez.
2. **`rules/stacking_rules.py::find_direct_supporting_placements`** y
   sus llamadores (`evaluate_stack_count`, `evaluate_supported_weight`,
   `_all_transitive_supporters`, y `fragility_rules.evaluate_fragility`
   que también lo usa indirectamente) — 65 164 llamadas, 8.295 s
   acumulados a través de sus distintos caminos de llamada. Es un
   diseño ya documentado de la fase 3 (recorrido O(n) de soportes), no
   un bug: **no se modifica en esta fase** (fuera de alcance: no es un
   bug real). La única palanca disponible es reducir cuántos
   candidatos llegan a evaluarse.
3. **`geometry/box.py::box_from_placement`** (4 598 029 llamadas,
   2.056 s de tiempo propio) y **`AxisAlignedBox.overlaps`**
   (1 236 150 llamadas, 1.883 s de tiempo propio) — invocadas
   masivamente desde dentro de `rules` (p. ej.
   `PlacementRuleContext.existing_boxes`, recalculada en cada acceso:
   50 993 llamadas, 2.004 s acumulados) y desde `geometry.support`.
   Tampoco se modifican (capa `geometry` congelada); se benefician
   indirectamente de cualquier reducción del número de candidatos
   evaluados.
4. Cálculo de soporte (`geometry/support.py::support_ratio`,
   `support_area_cm2`, `horizontal_overlap_area_cm2`) — coste
   significativo pero proporcional al número de candidatos, no un
   defecto propio; se beneficia igual que el punto 3.

### Conclusión del perfilado

La optimización de mayor impacto y menor riesgo es **cachear
incrementalmente el bounding box del layout aceptado** dentro de
`PackingState`, en vez de recalcularlo desde cero para cada candidato.
La segunda palanca disponible, dado que gran parte del coste restante
vive dentro de `rules` (fuera de alcance de modificación), es
**reducir el número de candidatos que llegan a evaluarse**: poda de
puntos candidatos claramente inválidos y un filtro rápido de
colisión/límites antes de construir el `PlacementRuleContext`
completo — sin duplicar ninguna semántica de `rules`/`geometry`, solo
evitando invocarla cuando el resultado ya es previsible.

## Objetivo de esta fase

- Obligatorio: 100 instancias, al menos 5x más rápido que los 102.635 s
  medidos arriba (es decir, ≤ ~20.5 s).
- Deseable: 100 instancias en menos de 5 s; 250 instancias en un
  tiempo práctico; 500 instancias sin necesitar decenas de minutos de
  espera.
- Sin sacrificar corrección: mismos `packed_count`, mismas razones de
  `UnpackedUnit`, mismo determinismo, mismo cumplimiento de reglas. Ver
  `docs/OptimizerPerformance.md` (post-optimización) para los
  resultados finales frente a estos objetivos.
