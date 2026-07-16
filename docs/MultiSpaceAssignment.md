# Asignación automática multi-espacio (OPT-01)

Implementa el ítem **OPT-01** de `docs/ProductBacklog.md`: dado un
pedido completo (no un único espacio ya elegido), calcular
automáticamente cuántos `LoadingSpace` hacen falta y qué va en cada
uno. Primer caso de uso real de la capa `application` — ver
`docs/Architecture.md`, sección `application`, y ADR-0001. Desde el
cierre hacia beta, también integrado en `presentation/desktop` — ver
§9.

## 1. Qué resuelve y qué no

`PackingEngine.optimize(...)` (capa `optimization`, sin cambios en esta
fase) responde "¿qué cabe en este espacio concreto?". No responde
"¿cuántos espacios necesito para este pedido completo?" — esa es
exactamente la pregunta que hace un forwarder o un planificador, y que
`MultiSpaceAssignmentEngine` (capa `application`, nueva) resuelve
orquestando varias llamadas a `PackingEngine.optimize(...)`.

`MultiSpaceAssignmentEngine` **nunca** reimplementa búsqueda de
colocación, geometría ni reglas de negocio: cada espacio individual se
resuelve exactamente igual que hoy, con el mismo `RulesEngine` y la
misma estrategia `greedy_extreme_point_v1`. Lo único nuevo es la
orquestación de "cuántas veces hace falta llamar al motor, con qué
espacio y con qué queda pendiente cada vez".

Fuera de alcance de esta fase (ver `docs/ProductBacklog.md`, OPT-01,
criterios de aceptación no cubiertos y dependencias):

- Minimización **exacta** del número de espacios usados (bin-packing
  de contenedores es NP-duro; se usa un heurístico determinista, ver
  §3).
- Secuenciación multi-parada / LIFO por ruta de reparto (`LOG-03`,
  depende de esta fase pero es un ítem propio).
- Sugerencia automática del tipo de espacio más adecuado (`LOG-05`).
- Guardar el resultado multi-espacio dentro de `.cargo3d` (ver §9):
  la interfaz avisa explícitamente que todavía no se persiste.
- Informes PDF/Excel específicos de multi-espacio: se usan los
  exportadores existentes, sin ningún formato nuevo.

## 2. Diseño: por qué vive en `application`, no en `optimization`

`ADR-0008` fija que `optimization` resuelve *dónde colocar cada
instancia dentro de un único `LoadingSpace` dado*. Decidir *cuántos
`LoadingSpace` hacen falta y en qué orden se usan* es una orquestación
de casos de uso — exactamente la responsabilidad que `docs/Architecture.md`
asigna a `application` desde la fase 1, aunque hasta ahora ese paquete
estuviera vacío. Meter esta lógica dentro de `optimization` habría
mezclado dos preguntas distintas ("¿dónde entra esto?" vs. "¿cuántas
veces hace falta repetir la pregunta anterior?") en un único paquete,
y habría forzado a `PackingStrategy` a saber de una noción — "varios
espacios candidatos" — que no le compete.

`application` pasa a depender de `optimization` además de `domain`
(ya lo permitía el contrato de capas de `import-linter`, que nunca
llegó a ejercitarse hasta ahora): `MultiSpaceAssignmentEngine` importa
`PackingEngine`, `PackingRequest` y `CancellationToken` tal cual están,
sin ninguna modificación.

## 3. Algoritmo

Determinista, sin búsqueda combinatoria — mismo espíritu que
ADR-0008/ADR-0009 (el resto del motor tampoco intenta encontrar el
óptimo global, sino un resultado bueno y reproducible en tiempo
razonable):

1. `remaining_units` empieza siendo `request.load_units` completo.
2. Mientras queden `remaining_units`:
   a. Si se canceló o se alcanzó `max_spaces`, se detiene.
   b. Se ejecuta el `PackingEngine` sobre **todos** los
      `request.loading_space_candidates` de esta ronda (nunca se
      descarta uno por ser "el primero que funciona") y se elige el
      mejor resultado con esta clave de comparación, en este orden
      exacto:
      1. mayor `packed_count` (más unidades cargadas);
      2. mayor `used_volume_cm3`;
      3. mayor `used_weight_kg`;
      4. menor `loading_space.capacity_volume_cm3` — a igualdad de lo
         anterior, no desperdiciar un espacio más grande de lo
         necesario;
      5. orden original de `loading_space_candidates` — desempate
         final, para que el resultado sea siempre reproducible incluso
         si dos candidatos empatan en todo lo demás.
   c. Si ningún candidato coloca nada, la carga restante es imposible
      con los candidatos disponibles: se detiene.
   d. Lo que no cupo en el espacio elegido de esta ronda
      (`PackingResult.unpacked_units`) se convierte en la nueva
      `remaining_units` para la ronda siguiente, recalculando
      `quantity` por SKU (`dataclasses.replace`, mismo `id` de
      `LoadUnit`).
3. Se repite hasta vaciar `remaining_units` o hasta alguna condición
   de parada.

Minimizar el número de espacios usados de forma **exacta** exigiría
explorar combinaciones de asignación — no determinista de forma
barata y fuera de alcance (ver `docs/ProductBacklog.md`, OPT-01,
Esfuerzo/Riesgo técnico). Elegir, ronda a ronda, el candidato que
mejor aprovecha lo que queda por cargar (en vez de detenerse en el
primero que sirve, o en vez de buscar combinaciones completas) ya es
una aproximación mucho más razonable y sigue siendo barata: el costo
adicional es lineal en el número de candidatos, no exponencial — ver
§8 para el análisis de costo.

### Por qué evaluar todos los candidatos, no detenerse en el primero que sirve

La primera versión de este motor probaba los candidatos en el orden
declarado por el usuario y se quedaba con el primero que colocara
*algo*, aunque fuera solo una unidad. Eso podía llevar a resultados
pobres: si el candidato preferido cabía "un poco" pero un candidato
más grande, más adelante en la lista, cabía "todo o casi todo", el
motor igual elegía el primero — desperdiciando capacidad y generando
más espacios de los necesarios. Evaluar siempre todos los candidatos y
elegir el que realmente carga más resuelve ese problema sin introducir
ninguna heurística nueva: sigue siendo "un resultado por ronda, sin
combinar rondas entre sí", solo que la ronda ahora compara en vez de
conformarse con el primero.

Con un solo candidato (el caso más común: "usa siempre contenedores de
40 pies") el comportamiento no cambia: el algoritmo se reduce
igualmente a "repite el mismo tipo de espacio tantas veces como haga
falta" — el criterio de aceptación explícito de OPT-01.

## 4. Distinción clave: `space_results[i].unpacked_units` vs. `final_unpacked_units`

`MultiSpaceAssignmentResult.space_results` es una tupla de
`PackingResult`, uno por espacio realmente usado. El
`unpacked_units` de una ronda intermedia **no** significa "esto nunca
se cargó": significa "esto no cupo en *este* espacio en concreto" y se
reintenta en el siguiente. Solo `MultiSpaceAssignmentResult.
final_unpacked_units` representa instancias definitivamente sin cargar
— reconstruidas al final, no leídas de ningún `space_results[i]`
concreto, precisamente para no confundir ambos conceptos.

## 5. Cancelación, límites y progreso

- `cancellation_token: CancellationToken | None` — el mismo tipo que
  ya usa `optimization` (`threading.Event`, sin PySide6). Se pasa tal
  cual a cada `PackingEngine.optimize(...)`; entre espacios, el bucle
  de `assign(...)` también comprueba `is_cancelled()` antes de empezar
  uno nuevo. Cancelar a mitad de un espacio deja ese espacio con lo que
  ya se alcanzó a colocar (igual que cancelar un `PackingEngine.optimize(...)`
  suelto hoy).
- `max_spaces: int | None` en `MultiSpaceAssignmentRequest` — límite de
  seguridad opcional, mismo patrón que `max_iterations` en
  `PackingRequest`.
- `progress_callback: Callable[[MultiSpaceProgress], None] | None` —
  se invoca una vez por espacio completado (no por instancia
  individual: eso ya lo cubre, dentro de cada espacio, el
  `progress_callback` propio de `PackingEngine`, que esta capa no
  reexpone). Una excepción del callback se convierte en advertencia y
  la ejecución continúa — mismo criterio que
  `GreedyExtremePointStrategy._emit_progress`.

## 6. API pública

```python
from cargo_optimizer.application import (
    MultiSpaceAssignmentEngine,
    MultiSpaceAssignmentRequest,
    MultiSpaceAssignmentResult,
    MultiSpaceStopReason,
)

request = MultiSpaceAssignmentRequest(
    loading_space_candidates=(mi_contenedor_40_pies,),
    load_units=mis_load_units,
)
result = MultiSpaceAssignmentEngine().assign(request)

result.spaces_used_count                      # cuántos espacios hicieron falta
result.is_fully_packed                        # True si no quedó nada sin cargar
result.space_results                          # un PackingResult por espacio usado
result.final_unpacked_units                   # instancias definitivamente sin cargar

# Resumen global (todo calculado a partir de space_results/
# final_unpacked_units, nunca guardado por separado):
result.spaces_used_by_candidate_name          # {"Contenedor 40 pies": 3, ...}
result.total_capacity_volume_cm3              # volumen total disponible
result.total_used_volume_cm3                  # volumen total utilizado
result.overall_volume_utilization_percent     # % global de ocupación de volumen
result.total_used_weight_kg                   # peso total cargado
result.overall_weight_utilization_percent     # % global de peso, o None si ningún
                                               #   espacio usado declara max_weight_kg
result.average_volume_utilization_percent     # ocupación promedio entre espacios
result.max_volume_utilization_percent         # ocupación máxima de un espacio
result.min_volume_utilization_percent         # ocupación mínima de un espacio
result.pending_count                          # len(result.final_unpacked_units)
result.execution_time_seconds                 # tiempo total del proceso completo
result.stop_reason                            # por qué se detuvo la asignación
```

`MultiSpaceStopReason` (`all_packed` / `impossible_remaining` /
`max_spaces_reached` / `cancelled`) explica por qué se detuvo la
asignación completa — no confundir con `UnpackedReason`
(`cargo_optimizer.optimization.codes`), que explica por qué una
instancia concreta no cargó dentro de un único espacio.

## 7. Pruebas

`tests/application/test_models.py` cubre las invariantes de
`MultiSpaceAssignmentRequest` (candidatos vacíos, rangos inválidos,
SKU/id duplicados). `tests/application/test_multi_space_assignment.py`
cubre: un solo espacio basta, hacen falta varios, imposibilidad total,
tope `max_spaces`, cancelación entre espacios, fallback cuando un
candidato no coloca nada, selección del mejor candidato aunque el
primero de la lista ya coloque algo (con un control que confirma que
esa elección produce menos espacios en total), los tres niveles de
desempate (capacidad menor, y finalmente orden original), determinismo
entre ejecuciones, progreso por espacio, resiliencia ante una
excepción del callback de progreso, pedido vacío, y las propiedades
agregadas nuevas (`spaces_used_by_candidate_name`,
`overall_weight_utilization_percent` con y sin límite declarado,
`average`/`max`/`min_volume_utilization_percent`, `pending_count`).

## 8. Costo computacional de evaluar todos los candidatos

La versión anterior de este algoritmo llamaba a
`PackingEngine.optimize(...)` como máximo una vez por candidato y por
ronda (se detenía en el primero que colocaba algo); la versión actual
llama **siempre** a los `N` candidatos declarados en cada ronda, así
que el costo total pasa de "hasta N" a "exactamente N" ejecuciones del
motor por ronda. Con un solo candidato (el caso de uso más común, ver
§3) no hay ningún costo adicional: sigue siendo una ejecución por
ronda. Con varios candidatos, el costo crece linealmente en `N`, nunca
exponencialmente — no hay ninguna combinación de espacios explorada,
solo `N` ejecuciones independientes comparadas al final de la ronda.
Dado que cada ejecución de `PackingEngine.optimize(...)` es, hoy, la
operación cara del sistema (ver `docs/OptimizerPerformance.md`), este
costo es real y proporcional a `N`: con pedidos grandes y varios tipos
de espacio candidatos, evaluar todos en cada ronda puede notarse. Se
acepta este costo porque (a) el caso de uso principal de OPT-01 es un
único tipo de espacio preferido, donde no hay ningún costo adicional,
y (b) la calidad del resultado (menos espacios usados en total, ver el
ejemplo de §3) generalmente compensa con creces el costo de `N`
ejecuciones extra por ronda frente a arrastrar un resultado subóptimo
durante todas las rondas siguientes.

## 9. Integración en `presentation/desktop`

Cierre hacia beta: `MultiSpaceAssignmentEngine` ya es utilizable desde
la interfaz de escritorio, no solo desde código. Mismo patrón que la
optimización de un solo espacio (fase 5.1): un `QThread` dedicado,
cancelación cooperativa vía `CancellationToken`, nunca se ejecuta en el
hilo de la interfaz.

- **`workers/multi_space_optimization_worker.py`** —
  `MultiSpaceOptimizationWorker`: calca `OptimizationWorker` (mismas
  señales, mismo patrón de un hilo por ejecución), envolviendo
  `MultiSpaceAssignmentEngine.assign(...)` en vez de
  `PackingEngine.optimize(...)`. No es un segundo sistema de
  threading — es el mismo, aplicado al caso de uso de `application`.
- **`dialogs/multi_space_setup_dialog.py`** — `MultiSpaceSetupDialog`:
  el usuario elige uno o varios candidatos (el espacio actual del
  formulario, más los perfiles activos del catálogo si hay uno
  disponible), los ordena con "Subir"/"Bajar" — ese orden es
  exactamente el orden de preferencia que usa el algoritmo (ver §3) —
  y fija `max_spaces` de forma opcional.
- **`panels/multi_space_results_panel.py`** — `MultiSpaceResultsPanel`:
  nueva pestaña "Multi-espacio" junto a "Resumen"/"No cargados"/
  "Avisos"/"Registro". Muestra el resumen global completo
  (`spaces_used_count`, `spaces_used_by_candidate_name`,
  `total_requested_count`/`total_packed_count`/`pending_count`,
  volumen disponible/utilizado, `overall_volume_utilization_percent`,
  `total_used_weight_kg`, `min`/`average`/`max_volume_utilization_percent`,
  `stop_reason`, `execution_time_seconds` — todo lo que expone
  `MultiSpaceAssignmentResult`, sin duplicar nada) y un selector
  "Espacio 1"…"Espacio N" con el resumen, avisos y no-cargados de ese
  `PackingResult` individual. El panel no toca el visor 3D: emite
  `space_selected(int)` y `MainWindow` decide cómo actualizarlo, mismo
  desacoplo que ya usa `viewer_widget.placement_selected`.
- **`MainWindow`** — acción "Optimización &multi-espacio…" (`F6`) en el
  menú Optimización. Mutuamente excluyente con "Ejecutar optimización"
  (un solo worker de cualquiera de los dos tipos a la vez —
  `_is_any_optimization_running()`); "Cancelar" cancela el que esté
  corriendo. Al terminar, se muestra el espacio 1 en el visor 3D y la
  pestaña "Multi-espacio" pasa a primer plano.

### Persistencia: explícitamente fuera de esta fase

`.cargo3d` no cambia: `CargoProject`/`ProjectFileRepository` siguen
guardando únicamente el último resultado de un solo espacio
(`latest_result`). Si el usuario guarda el proyecto mientras hay un
resultado multi-espacio activo, `MainWindow` muestra un aviso
explícito ("Los resultados multi-espacio todavía no se guardan dentro
del proyecto.") y continúa guardando el resto del proyecto con
normalidad — no bloquea el guardado, solo informa. Persistir el
resultado multi-espacio dentro de `.cargo3d` (o exportarlo a PDF/Excel
con un formato propio) queda para un encargo posterior explícito.
