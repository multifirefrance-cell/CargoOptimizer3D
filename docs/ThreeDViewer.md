# Visor 3D (implementación real, fase 6.1)

Este documento describe lo que existe hoy en
`presentation/desktop/viewer/` y `presentation/desktop/panels/selection_details_panel.py`.
El diseño original que motivó esta implementación está en
`docs/ThreeDViewerDesign.md` (fase 6.0); el reparto entre 6.1/6.2/6.3
está en `docs/ThreeDViewerImplementationPlan.md`. Las decisiones
estructurales están en ADR-0010 (tecnología) y ADR-0011 (desacoplo del
motor y fallback).

## 1. Dependencias

```toml
dependencies = [
    "PySide6>=6.7,<7",
    "pyvista>=0.48,<1",
    "pyvistaqt>=0.12,<1",
    "vtk>=9.6,<10",
]
```

Versiones instaladas y verificadas en esta fase: pyvista 0.48.4,
pyvistaqt 0.12.0, vtk 9.6.2, PySide6 6.11.1, Python 3.12.10. Sin
conflictos de compatibilidad — no hizo falta desviarse de la
tecnología elegida en ADR-0010.

## 2. Estructura

```
presentation/desktop/
├── viewer/
│   ├── __init__.py
│   ├── models.py             # SceneModel, PlacementVisualModel
│   ├── constants.py          # paleta, opacidades, grosores, colores por tema
│   ├── color_registry.py     # ColorRegistry: color por SKU determinista
│   ├── scene_builder.py      # SceneBuilder: PackingResult -> SceneModel
│   ├── scene_controller.py   # SceneController: Plotter, actores, picking, cámara
│   └── widget.py             # Packing3DViewer(QWidget): contrato público + fallback
└── panels/
    └── selection_details_panel.py
```

`viewport_3d_placeholder.py` se eliminó: `Packing3DViewer` ocupa su
lugar en `work_area_splitter` y trae su propio contenido de repuesto
integrado (sección 8).

## 3. Modelo de escena (`models.py`)

```python
@dataclass(frozen=True, slots=True)
class PlacementVisualModel:
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
    loading_space: LoadingSpace
    placement_visuals: tuple[PlacementVisualModel, ...]
    selected_sequence_number: int | None = None
    container_visible: bool = True
    boxes_visible: bool = True
    axes_visible: bool = True
    color_mapping: dict[str, str] = field(default_factory=dict)
```

`instance_number` se añadió más allá de la lista de campos del encargo
de la fase 6.1: `SelectionDetailsPanel` (sección 13 del mismo encargo)
exige mostrar "instancia" y "secuencia de carga" como datos distintos,
y ambos ya existen en `Placement` (`instance_number`,
`sequence_number`) — omitir el campo habría obligado a mostrar el
mismo número bajo dos etiquetas, un dato engañoso. `Placement` no se
tocó: el campo ya existía en `domain`.

## 4. `ColorRegistry`

- Un `color_hex` válido en el `LoadUnit` (validado con una expresión
  regular `#RRGGBB`/`#RGB`) se usa tal cual.
- Si es inválido o falta, se deriva un color de una paleta fija de 20
  colores mediante `zlib.crc32(sku) % len(paleta)` — determinista
  entre ejecuciones y procesos, a diferencia de `hash()` de Python
  (aleatorizado por `PYTHONHASHSEED` desde Python 3.3).
- `selection_color(theme)` y `edge_color(theme)` son colores
  separados, con variante para tema claro y oscuro.

## 5. `SceneBuilder`

```python
SceneBuilder().build(result: PackingResult, load_units_by_id: Mapping[UUID, LoadUnit]) -> SceneModel
```

Función determinista sin dependencia de Qt ni VTK (probada con pytest
puro, sin plataforma offscreen). Por cada `Placement`, busca el
`LoadUnit` en `load_units_by_id` por `load_unit_id`:

- Si existe: traduce todos los campos reales, incluida la posición y
  las dimensiones orientadas ya calculadas por `Placement`
  (`x_cm`/`y_cm`/`z_cm`, `length_cm`/`width_cm`/`height_cm`) — nunca
  recalcula geometría ni vuelve a evaluar reglas de negocio.
- Si no existe (referencia colgante): produce un `PlacementVisualModel`
  genérico (`sku="?"`, `name="Desconocido"`, `weight_kg=0.0`) con un
  color determinista igualmente — nunca lanza una excepción.

## 6. `SceneController`

Posee el `Plotter`/`QtInteractor` (aceptado como `PyVistaPlotterLike`,
un `Protocol` estructural — así acepta tanto un `QtInteractor` real
como un `pyvista.Plotter(off_screen=True)` en pruebas) y es responsable,
únicamente, de: construir/eliminar actores, visibilidad, selección,
cámara, tema, limpieza de recursos. No conoce `MainWindow` ni duplica
lo que hace `SceneBuilder`.

- **`LoadingSpace`**: suelo (`pv.Plane`), cuatro paredes semitransparentes,
  alambre exterior (`pv.Box` en modo `wireframe`), puerta destacada
  según `DoorPosition` (sin resaltado si es `UNRESTRICTED`), tres ejes
  XYZ desde el origen. Sin permutar ejes: X = largo, Y = ancho, Z =
  altura, igual que en `domain`.
- **Cajas**: un actor por `Placement` (no agrupado por SKU en esta
  fase), color por SKU, borde fino, nombre de actor
  `viewer-box-{sequence_number}` para poder localizarlo. La conversión
  de la esquina mínima de `Placement` a centro+longitudes de
  `pv.Cube` (`cube_center_and_lengths`) respeta exactamente
  `min_x = placement.x_cm`, `max_x = placement.x_cm + placement.length_cm`
  (e Y/Z análogos) — cubierta por pruebas dedicadas.
- **Picking**: clic sobre una caja identifica el actor, lo resalta
  (borde + `SELECTION_LINE_WIDTH` + `selection_color`), restaura el
  estilo del actor previamente seleccionado, y notifica
  `sequence_number` a través de un callback interno. Clic en espacio
  vacío deselecciona y notifica `None`. `SceneController.load_scene`
  llama a `disable_picking()` antes de `enable_mesh_picking(...)` para
  que recargar la escena (p. ej. al cambiar de tema) no lance
  `PyVistaPickingError: Picking is already enabled`.
- **Selección programática** (`set_selected_placement`) resalta el
  actor pero **no** invoca el callback — evita un ciclo de señal entre
  `MainWindow` y el propio widget cuando la selección se origina fuera
  del picking (p. ej. una futura tabla de cajas).
- **Cámara**: `reset_camera()` usa `view_isometric()` +
  `camera.up = (0, 0, 1)` + `reset_camera()` de PyVista, para encuadrar
  todo el espacio con Z hacia arriba. `focus_placement(sequence_number)`
  encuadra la cámara sobre los límites del actor de esa caja
  (`reset_camera(bounds=actor.GetBounds())`) — implementado ya en 6.1,
  no aplazado a 6.2 como decía el diseño original (ver nota en
  `docs/ThreeDViewerDesign.md`).
- **Tema**: `apply_theme(theme)` cambia el color de fondo y, si hay una
  escena cargada, la reconstruye por completo (no hay forma barata de
  recolorear todos los actores sin reconstruir en PyVista/VTK para
  este alcance).

## 7. `Packing3DViewer` (widget público)

Contrato completo, todos los métodos no-op seguros cuando
`is_available()` es `False`:

```python
class Packing3DViewer(QWidget):
    placement_selected = Signal(object)  # int | None

    def display_result(self, result: PackingResult, load_units_by_id: Mapping[UUID, LoadUnit]) -> None
    def clear_scene(self) -> None
    def reset_camera(self) -> None
    def set_container_visible(self, visible: bool) -> None
    def set_boxes_visible(self, visible: bool) -> None
    def set_axes_visible(self, visible: bool) -> None
    def set_selected_placement(self, sequence_number: int | None) -> None
    def focus_placement(self, sequence_number: int) -> None
    def find_placement_visual(self, sequence_number: int) -> PlacementVisualModel | None
    def set_dark_theme(self, enabled: bool) -> None
    def is_available(self) -> bool
    def unavailable_reason(self) -> str | None
    def shutdown(self) -> None
```

`set_dark_theme(enabled: bool)` sustituye a `apply_theme(theme: str)`
del diseño original — el encargo de la fase 6.1 lo especificó así
explícitamente; es un refinamiento de alcance, no una decisión de
arquitectura reabierta.

`placement_selected` está tipado `Signal(object)`, no
`Signal(int | None)`: PySide6 6.11 acepta `Signal(int | None)` en la
definición de la clase, pero lanza
`TypeError: placement_selected() only accepts 0 argument(s), 1 given!`
al emitir un `int` o un `None` con esa firma. `Signal(object)` funciona
para ambos casos — mismo patrón ya usado en `OptimizationWorker`
(fase 5.1).

## 8. Fallback sin 3D disponible

`_try_create_interactor` decide, en este orden:

1. Si `QApplication.platformName() == "offscreen"`: 3D no disponible,
   motivo explícito ("La plataforma Qt activa es 'offscreen'..."). Ver
   sección 10 sobre por qué esto se comprueba **antes** de intentar
   nada, no dentro de un `try/except`.
2. Si `from pyvistaqt import QtInteractor` falla: 3D no disponible,
   motivo = el `ImportError`.
3. Si `QtInteractor(self)` lanza cualquier excepción (driver gráfico
   ausente, contexto OpenGL no inicializable): 3D no disponible, motivo
   = la excepción.

En cualquiera de los tres casos, `Packing3DViewer` construye un
contenido de repuesto (`objectName="packing3DViewerFallback"`): icono
de advertencia, título "Vista 3D no disponible", y el motivo técnico
real en texto — nunca se oculta la causa. El resto de la aplicación
(optimizar, ver resultados numéricos, tablas) sigue funcionando con
normalidad.

## 9. Integración con `MainWindow`

- `Packing3DViewer` sustituye al placeholder en `work_area_splitter`;
  `SelectionDetailsPanel` vive en un `QDockWidget` nuevo
  (`selectionDetailsDock`) en el lado derecho, con visibilidad y
  geometría persistidas por `QSettings` igual que el resto de docks.
- Menú Ver: nuevas acciones para resetear cámara, mostrar/ocultar
  espacio de carga, cajas y ejes (`QAction` checkable, estado inicial
  `True`), y mostrar/ocultar el panel de detalles
  (`toggleViewAction()` del propio dock).
- `_on_run_optimization`: limpia el visor y el panel de detalles al
  iniciar, igual que ya limpiaba `results_panel`/`unpacked_table_panel`/
  `warnings_panel` desde la fase 5.1.
- `_on_optimization_finished(result)`: limpia el panel de detalles y
  llama a `viewer_widget.display_result(result, self._last_load_units_by_id)`
  — el mismo mapping `UUID -> LoadUnit` que `UnpackedUnitTableModel` ya
  usa desde la fase 5.1, sin ninguna estructura de datos nueva.
- `_on_placement_selected(sequence_number)`: busca el
  `PlacementVisualModel` correspondiente vía
  `viewer_widget.find_placement_visual(...)` y actualiza
  `selection_details_panel` (o lo limpia si `sequence_number` es
  `None` o no se encuentra).
- `_set_theme(theme)`: además de aplicar la paleta/QSS de la
  aplicación (fase 5.0), llama a `viewer_widget.set_dark_theme(...)`.
- `_on_new_project()`: limpia el visor y el panel de detalles.
- `closeEvent`: llama a `viewer_widget.shutdown()` antes de cerrar. Es
  una llamada explícita porque `Packing3DViewer` es un widget hijo
  embebido en un layout, no una ventana de nivel superior — Qt nunca
  le entrega un `closeEvent` propio cuando `MainWindow` se cierra.

## 10. Hallazgo técnico: segmentation fault de VTK bajo `offscreen`

Durante la implementación se descubrió que construir un
`pyvistaqt.QtInteractor` mientras `QT_QPA_PLATFORM=offscreen` está
activo (el modo que usa toda la suite de pruebas para no requerir una
GPU/sesión gráfica) provoca un **segmentation fault nativo de Windows**
(`vtkWin32OpenGLRenderWindow: failed to get valid pixel format`, salida
con código 139), no una excepción Python capturable. La causa: VTK
necesita un identificador de ventana nativo real para embeber su
contexto OpenGL, y la plataforma "offscreen" de Qt deliberadamente no
crea ninguna ventana nativa.

Verificado explícitamente:

- En la plataforma nativa de Qt (con una sesión gráfica real),
  `QtInteractor` se construye sin problema — confirmado con el script
  de diagnóstico de la sección 11.
- Un `pyvista.Plotter(off_screen=True)` normal (sin `QtInteractor`, sin
  embeber en un `QWidget`) **sí** funciona con seguridad bajo
  `offscreen` — es la base de las pruebas reales de `SceneController`
  (`test_scene_controller.py`).

Mitigación: `Packing3DViewer._try_create_interactor` comprueba
`QApplication.platformName() == "offscreen"` **antes** de importar o
construir nada de `pyvistaqt`, tratando ese caso proactivamente como
"3D no disponible" en vez de confiar en un `try/except` que nunca
habría podido interceptar el crash.

## 11. Smoke test real (plataforma nativa, no `offscreen`)

Verificado manualmente en esta sesión, sobre la máquina Windows real
del usuario (sin `QT_QPA_PLATFORM` forzado):

- `python -m cargo_optimizer` arranca sin errores en `stdout`/`stderr`
  y mantiene un proceso estable (memoria ~379 MB, consistente con
  VTK/PyVista cargado) con el título de ventana
  `CargoOptimizer3D v0.9.0` — confirmado con `tasklist`.
- Un script de diagnóstico puntual
  (`Packing3DViewer()` construido bajo `app.platformName() == "windows"`)
  confirma `is_available() == True` y `unavailable_reason() is None`:
  el `QtInteractor` real se inicializa correctamente en producción, sin
  caer en modo de repuesto. `shutdown()` no lanza excepción.

**Lo que no se pudo verificar en este entorno**: interacción real con
el ratón (clic sobre una caja para seleccionar, arrastrar la cámara),
inspección visual del renderizado (colores, geometría, iluminación),
y el comportamiento exacto del cierre de ventana con un proceso VTK
activo más allá de que el proceso no queda colgado tras `taskkill`. El
entorno de este agente no tiene automatización de UI de escritorio
(solo de navegador) — no hay una herramienta disponible para
"capturar pantalla del escritorio" ni "hacer clic en una ventana
nativa de Windows". Esta limitación se declara explícitamente en vez
de darse por verificada.

## 12. Rendimiento medido (orientativo, sin umbrales de aprobación)

Medido con un script puntual (no forma parte de la suite de pytest,
sin umbrales frágiles) que construye una escena con N cajas idénticas
y mide `SceneBuilder().build(...)` y
`SceneController.load_scene(...)` contra un
`pyvista.Plotter(off_screen=True)`, en la misma máquina de desarrollo:

| N placements | `SceneBuilder.build` | `SceneController.load_scene` |
|---:|---:|---:|
| 10  | 0.07 ms | 86 ms |
| 100 | 0.37 ms | 486 ms |
| 500 | 2.41 ms | 3988 ms |

`SceneBuilder.build` es, como se esperaba, prácticamente gratis (es
Python puro sobre datos ya calculados). `SceneController.load_scene`
crece de forma aproximadamente lineal con el número de cajas —
consistente con la estrategia "un actor por caja" documentada en
`docs/ThreeDViewerDesign.md` (sección 9.1) como válida para esta fase,
con agrupación/instancing explícitamente aplazada a la fase 6.3 si el
uso real lo justifica. Con 500 cajas, cargar una escena tarda del
orden de 4 segundos — perceptible pero no bloqueante para una
optimización típica de decenas a un par de cientos de instancias
(ver `docs/OptimizerPerformance.md` para los volúmenes de referencia
del propio motor). No se fija ningún umbral de fallo en pytest sobre
estos números, tal como pedía el encargo de la fase.

## 13. Limitaciones conocidas / próximas fases

- Un actor VTK por caja, sin agrupar por SKU ni usar *instancing* —
  aceptable en esta fase, candidato a revisar en 6.3 si el uso real
  con miles de cajas lo requiere (ver sección 12).
- Sin filtros (por SKU, por capa, ocultar seleccionados, solo no
  cargados), sin etiquetas 3D, sin modos de color alternativos (peso,
  orden de carga, fragilidad), sin vistas de cámara predefinidas más
  allá del encuadre automático, sin captura de imagen, sin animación —
  todo explícitamente aplazado a 6.2/6.3, ver
  `docs/ThreeDViewerImplementationPlan.md`.
- El fallback por plataforma `offscreen` es intencional y permanente
  (no es un "bug pendiente de arreglar"): es la mitigación correcta al
  hallazgo de la sección 10, no una limitación temporal del entorno de
  pruebas.

## 14. Pruebas

61 pruebas nuevas en `tests/presentation/desktop/`:

- `test_color_registry.py` (9): sin Qt ni VTK.
- `test_scene_builder.py` (10): función pura sobre datos de dominio,
  sin Qt ni VTK.
- `test_scene_controller.py` (18): contra un
  `pyvista.Plotter(off_screen=True)` real (renderizado VTK real,
  seguro bajo `offscreen` porque no pasa por `QtInteractor`) —
  construcción de escena, visibilidad, selección externa vs. picking,
  cámara, tema, cierre.
- `test_packing_3d_viewer_widget.py` (7): comportamiento determinista
  de modo de repuesto bajo `offscreen` (motivo, no-ops seguros, señal,
  `shutdown` idempotente).
- `test_selection_details_panel.py` (6): estado vacío, todos los
  campos, distinción `instance_number` vs. `sequence_number`,
  `clear()`.
- `test_main_window_viewer_integration.py` (11): orquestación real de
  `MainWindow` sobre el visor y el panel de detalles (construcción,
  acciones del menú Ver, limpieza al optimizar/nuevo proyecto,
  `display_result` recibe el resultado y el mapping correctos,
  enrutado de la señal `placement_selected`, `shutdown` en
  `closeEvent`, propagación de tema) — todas verificables bajo
  `offscreen` porque prueban las llamadas que `MainWindow` hace al
  widget, no el renderizado en sí.

443 pruebas en verde en total (`pytest -q`).
