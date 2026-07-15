# Plan de implementación del visor 3D

Desglose en tres entregas a partir del diseño de la fase 6.0
(`docs/ThreeDViewerDesign.md`). Ninguna de las tres está implementada
todavía — este documento es el plan, no el registro de lo hecho.

## Fase 6.1 — Implementación mínima

Objetivo: sustituir el placeholder por un visor real, funcional de
principio a fin, con el conjunto más pequeño de funciones que sigue
siendo útil.

1. **Dependencia**: añadir `pyvista` y `pyvistaqt` a
   `pyproject.toml` (`dependencies`, no `dev`) — confirmar en ese
   momento la compatibilidad exacta de versiones con Python 3.12 y
   PySide6 6.7+ (ver ADR-0010, riesgo aceptado nº 2).
2. **`viewer/models.py`**: `SceneModel`, `PlacementVisualModel`
   (sección 5 del diseño).
3. **`viewer/color_registry.py`**: color por SKU determinista entre
   ejecuciones (hash estable, nunca `hash()` de Python ni `random`).
4. **`viewer/scene_builder.py`**: `build_scene(result,
   load_units_by_id) -> SceneModel` (sección 6 del diseño), con
   pruebas unitarias que no requieren Qt ni VTK.
5. **`viewer/scene_controller.py`**: posesión del `Plotter`/actores;
   construir `LoadingSpace` (suelo, paredes, alambre, puerta
   destacada — sin etiqueta de dimensiones, aplazada); construir cajas
   (actor por caja, sección 9); `reset_camera`; picking por clic
   (actor → `sequence_number`); selección visual (resalte de borde);
   visibilidad de contenedor/cajas/ejes.
6. **`viewer/widget.py`**: `Packing3DViewer(QWidget)` — contrato
   completo de la sección 4 salvo lo aplazado; captura de fallos de
   inicialización de PyVista/PyVistaQt/OpenGL → `is_available() ==
   False` + contenido de reemplazo (variante del placeholder actual con
   mensaje específico del motivo).
7. **`panels/selection_details_panel.py`**: formulario de solo lectura
   con los campos de la sección 12.1 del diseño.
8. **Integración con `MainWindow`**:
   - sustituir `self.viewport_3d_placeholder = Viewport3DPlaceholder(self)`
     por `self.viewer = Packing3DViewer(self)` en el mismo lugar del
     `work_area_splitter`;
   - `_on_optimization_finished` (ya existente, fase 5.1) pasa a llamar
     también `self.viewer.display_result(result,
     self._last_load_units_by_id)` y a limpiar/actualizar
     `SelectionDetailsPanel`;
   - `_on_run_optimization` limpia el visor y el panel de detalles al
     iniciar, igual que ya limpia `results_panel`/`unpacked_table_panel`/
     `warnings_panel`;
   - `_set_theme` (ya existente, fase 5.0) llama también a
     `self.viewer.apply_theme(theme)`;
   - `closeEvent` (ya existente) cierra el `Plotter` del visor junto al
     resto de la limpieza al cerrar la ventana;
   - `_on_toggle_3d_focus`/`_on_reset_layout` (ya existentes) no
     necesitan cambios: tratan el widget de la vista 3D genéricamente
     por posición en el splitter.
9. **Tests**: los cuatro niveles de la sección 22 del diseño —
   unitarios (`scene_builder`, `color_registry`, modelos), Qt offscreen
   sin GPU garantizada (creación, `is_available()` simulado, señales,
   destrucción), Qt offscreen con OpenGL condicional
   (`display_result` real, `pytest.skip` limpio si no hay contexto),
   integración con `MainWindow` (mismo patrón que
   `test_main_window_optimization.py`).

**Explícitamente fuera de 6.1** (aplazado, no olvidado): etiquetas,
vistas de cámara predefinidas más allá del encuadre automático,
captura de imagen, filtros (SKU/capa/no-cargados), modos de color
alternativos, animación, agrupación/instancing para escala.

## Fase 6.2 — Enriquecimiento

Depende de que 6.1 esté en uso real (para saber qué de esto realmente
hace falta primero, en vez de adivinarlo):

- **Filtros**: por SKU, por capa (rango de Z), ocultar seleccionados,
  mostrar solo no cargados (con una representación propia, ver diseño
  sección 13 — los `UnpackedUnit` no tienen `Placement`).
- **Etiquetas**: de dimensiones del `LoadingSpace`, opcionalmente por
  caja (SKU/secuencia).
- **Modos de color**: por peso, por orden de carga, por fragilidad, por
  tipo de empaque — reutilizando `ColorRegistry` con un modo de
  gradiente/categoría en vez del hash por SKU.
- **Vistas predefinidas**: isométrica, superior, frontal, lateral
  izquierda/derecha, desde la puerta (leyendo `door_position`) — aquí
  se evalúa extraer `viewer/camera_controller.py` (criterio de la
  sección 3.1 del diseño).
- **Captura de imagen**: `capture_image(path, ...)` (sección 18 del
  diseño), con vista isométrica automática para uso en reportes.

## Fase 6.3 — Escala y animación

Solo si el uso real (o el rendimiento futuro del optimizador, ver
`docs/OptimizerPerformance.md`) lo justifica:

- **Animación** por `sequence_number`: reproducir, pausar, avanzar,
  retroceder, velocidad, mostrar primeras N cajas, simular carga y
  descarga (sección 19 del diseño — el modelo de datos ya lo permite
  sin cambios).
- **Capas**: navegación por rango de altura.
- **Cortes**: planos de corte para inspeccionar el interior de una
  carga densa.
- **Explosión**: separar visualmente las cajas a lo largo de un eje
  para inspección.
- **Optimizaciones de escala**: malla combinada o glyphs/instancing
  (sección 9.1 del diseño) cuando actor-por-caja deje de ser razonable
  — aquí se evalúa extraer `viewer/picking_controller.py` (el picking
  pasa de actor a celda/punto) y `viewer/visibility_controller.py` (el
  estado de qué está visible deja de ser un booleano por caja).

## Trazabilidad con el encargo de fase 6.0

Este plan cubre exactamente la separación pedida (sección 24 del
encargo de fase 6.0): "Fase 6.1 mínima" / "Fase 6.2" / "Fase 6.3" con
el mismo contenido enumerado allí, ajustado donde el propio diseño
(`docs/ThreeDViewerDesign.md`) identificó una simplificación
justificada (p. ej. `camera_controller.py`/`picking_controller.py`/
`visibility_controller.py` no se crean hasta que su fase respectiva
los necesite de verdad).
