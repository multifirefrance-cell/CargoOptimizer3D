# ADR-0011: Desacoplo del visor 3D respecto al motor, y fallback sin 3D

## Estado

Aceptada — 2026-07-15

## Contexto

El visor 3D (`presentation/desktop/viewer/`, diseño completo en
`docs/ThreeDViewerDesign.md`) necesita, para representar un
`PackingResult`, datos de `LoadUnit` que `Placement` no referencia
directamente (solo `load_unit_id`) — el mismo problema que
`UnpackedUnit` ya planteó en la fase 5.1. Necesita además un
comportamiento definido para cuando la propia tecnología de
renderizado (ADR-0010) no puede inicializarse en la máquina del
usuario. Dos decisiones estructurales quedan registradas aquí.

## Decisión 1: API basada en datos ya calculados, nunca en el motor

`Packing3DViewer.display_result(result: PackingResult,
load_units_by_id: Mapping[UUID, LoadUnit]) -> None` es el único punto
de entrada de datos del visor. El visor no importa
`cargo_optimizer.optimization` (ni `PackingEngine`, ni
`PackingRequest`, ni `RulesEngine`, ni ningún optimizador), no ejecuta
nada, no persiste nada, no importa ni exporta nada — solo dibuja lo que
ya se decidió.

`load_units_by_id` se entrega junto al resultado, en vez de tres
alternativas descartadas explícitamente:

- ampliar `PackingResult` con los `LoadUnit` completos (modifica
  dominio sin necesidad real, y ya es una decisión de fase 2.1 que
  `Placement` referencie por `id`, no por valor);
- crear un DTO visual paralelo a `LoadUnit` (redundante mientras el
  DTO solo replicaría campos ya existentes);
- construir la escena desde `CargoProject` (acopla el visor a un
  agregado que el resto de la interfaz todavía no usa — `CargoProject`
  no forma parte del flujo real hasta la fase 7).

En su lugar, se reutiliza exactamente el patrón ya establecido en la
fase 5.1 para el mismo problema con `UnpackedUnit`
(`UnpackedUnitTableModel.set_unpacked_units(units, load_units_by_id)`):
`MainWindow` ya construye y conserva `self._last_load_units_by_id` al
lanzar cada optimización, así que entregárselo también al visor no
añade ninguna pieza nueva de dominio ni de orquestación.

Esta separación no la impone hoy `import-linter` de forma automática
(`presentation` puede legítimamente importar `optimization`, como ya
hace `workers/optimization_worker.py`): es una disciplina de diseño
documentada aquí y en `CLAUDE.md`, verificable en revisión de código,
no una regla forzada por herramientas.

## Decisión 2: fallback informativo, nunca un fallo total de la aplicación

`Packing3DViewer` captura cualquier fallo al inicializar PyVista,
PyVistaQt o el contexto OpenGL subyacente (biblioteca no instalada,
`QtInteractor` no inicializable, driver gráfico ausente o
incompatible). En ese caso, `is_available()` devuelve `False` y el
widget se comporta como un contenido de reemplazo informativo (variante
del placeholder ya existente hoy,
`presentation/desktop/panels/viewport_3d_placeholder.py`, con un
mensaje específico del motivo en vez de "disponible en la Fase 6").

Todos los métodos públicos del contrato (`display_result`,
`clear_scene`, `reset_camera`, `set_container_visible`,
`set_boxes_visible`, `set_axes_visible`, `set_selected_placement`,
`focus_placement`, `set_dark_theme`) se convierten en no-op seguros
cuando
`is_available()` es `False`. `MainWindow` nunca necesita comprobar
`is_available()` antes de llamarlos: el widget decide internamente si
hay algo que dibujar, igual que `MainWindow` ya trata los errores del
motor en la fase 5.1 (capturar en el punto más bajo posible, nunca
dejar que un subsistema tire la ventana entera).

## Consecuencias

**Beneficios:**

- El visor es probable de forma aislada (`SceneBuilder` es una función
  pura sobre datos de dominio, sin Qt ni VTK) y reemplazable sin tocar
  `MainWindow` más allá del punto de integración.
- Ninguna fase futura del motor (nuevas estrategias, índice espacial,
  cambios de rendimiento) puede romper el visor por acoplamiento
  accidental, porque el visor no conoce su existencia.
- La aplicación completa (optimización, resultados numéricos, tablas)
  sigue siendo utilizable en una máquina sin soporte 3D funcional —
  requisito explícito de la fase 6.0, no una mejora incidental.
- `MainWindow` no acumula lógica condicional de "¿el 3D funciona?" —
  esa responsabilidad queda contenida enteramente dentro del propio
  widget.

**Costes / riesgos aceptados:**

- El desacoplo de datos (`load_units_by_id` entregado explícitamente)
  exige que `MainWindow` mantenga esa correspondencia sincronizada con
  el resultado mostrado — el mismo riesgo, ya aceptado y ya resuelto,
  que existe desde la fase 5.1 para `UnpackedUnitTableModel`.
- El modo fallback significa que un fallo de inicialización de 3D es
  silencioso para el flujo de datos (no lanza, no se propaga): se
  acepta porque el objetivo explícito es que nunca bloquee el resto de
  la aplicación, pero exige que el mensaje de fallback sea
  suficientemente claro para que el usuario entienda que el visor no
  está disponible, no que "no hay nada que mostrar".
