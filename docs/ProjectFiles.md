# Persistencia de proyectos (`.cargo3d`, fase 7.0)

Este documento describe el formato real de archivo de proyecto y la
implementación de `ProjectFileRepository`
(`infrastructure/persistence/`), junto con cómo `MainWindow` lo usa
para que un usuario pueda crear, guardar, cerrar y reabrir un proyecto
días después y seguir trabajando exactamente donde lo dejó.

Esta fase es deliberadamente pequeña en alcance: JSON propio,
versionado, con backup automático y escritura atómica — nada de
SQLite, catálogos, Excel, PDF ni sincronización en la nube (eso es
trabajo de fases posteriores, ver `docs/Roadmap.md`).

## 1. Formato del archivo

Extensión `.cargo3d`. JSON UTF-8, indentado (`json.dumps(..., indent=2)`),
legible por un humano en cualquier editor de texto. Nunca `pickle`,
`jsonpickle` ni volcado de `__dict__` — cada tipo de dominio se traduce
explícitamente en `infrastructure/persistence/serialization.py`.

```json
{
  "format_name": "cargo_optimizer3d_project",
  "schema_version": "1.0",
  "application_version": "0.10.0",
  "created_at": "2026-07-15T10:00:00+00:00",
  "modified_at": "2026-07-15T11:30:00+00:00",
  "project": {
    "id": "…",
    "name": "mi_proyecto",
    "notes": "",
    "schema_version": "1.0",
    "loading_space": { "...": "..." },
    "load_units": [ { "...": "..." } ],
    "latest_result": { "...": "..." } | null
  },
  "presentation_state": {
    "result_stale": false,
    "ui_state": {
      "theme": "light",
      "splitters": { "main": "base64…", "workArea": "base64…", "leftWork": "base64…" },
      "docks_visible": { "projectTreeDock": true, "selectionDetailsDock": true }
    }
  }
}
```

- `format_name`: identifica el archivo como un proyecto de
  CargoOptimizer3D. Un valor distinto se rechaza como
  `ProjectFileCorruptError`, no como "otra versión".
- `schema_version`: versión del **esquema del archivo**, distinta de
  `application_version`. Un archivo puede sobrevivir a varias versiones
  de la aplicación mientras el esquema no cambie.
- `application_version`: la versión de CargoOptimizer3D que escribió
  el archivo por última vez (informativo, no se usa para decidir
  compatibilidad — eso es responsabilidad exclusiva de
  `schema_version`).
- `created_at`/`modified_at`: ISO 8601 con zona horaria (UTC).
  `created_at` se conserva a través de guardados sucesivos del mismo
  archivo (ver sección 3); `modified_at` se actualiza en cada guardado.
- `project`: el `CargoProject` completo (`id`, `name`, `notes`,
  `schema_version` de dominio, `LoadingSpace`, todos los `LoadUnit`, y
  el último `PackingResult` si existe — con sus `Placement`,
  `UnpackedUnit` y `warnings`).
- `presentation_state`: un diccionario **opaco para `infrastructure`**
  (ver sección 4) que `presentation/desktop` usa para guardar si el
  resultado quedó invalidado y el estado visual relevante (tema,
  splitters, qué docks están visibles).

## 2. Qué se guarda y qué no

**Se guarda** (todo mediante conversión explícita campo a campo, ver
`serialization.py`): `CargoProject` (nombre, notas, id), `LoadingSpace`,
todos los `LoadUnit`, el último `PackingResult` (incluidos todos los
`Placement`, `UnpackedUnit` y `warnings`), tema activo, tamaños de
splitters, qué paneles acoplables están visibles, si el resultado
mostrado está invalidado, y los metadatos de versión/fechas/UUID.

**Nunca se guarda**: hilos (`OptimizationWorker`/`QThread`), objetos Qt
(`QWidget`, `QDockWidget`, `QAction`...), nada de VTK/PyVista (actores,
`Plotter`, cámara), `CancellationToken`, cachés internas del motor de
optimización (`PackingState`), ni ningún objeto temporal de ejecución.
Todo eso se reconstruye en memoria al volver a ejecutar una
optimización o al reabrir el visor — nunca se serializa.

## 3. `ProjectFileRepository`

```python
class ProjectFileRepository:
    def save(
        self, project: CargoProject, path: Path, *,
        application_version: str,
        presentation_state: Mapping[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> ProjectFileMetadata: ...

    def load(self, path: Path) -> LoadedProjectFile: ...
    def validate(self, path: Path) -> ProjectFileMetadata: ...
    def backup(self, path: Path) -> Path | None: ...
```

- **Escritura atómica**: `save` escribe primero en un archivo temporal
  del mismo directorio (`tempfile.mkstemp`, mismo volumen que el
  destino) y lo reemplaza con `os.replace` — atómico tanto en Windows
  como en POSIX. Una escritura interrumpida a mitad (corte de luz,
  proceso matado) nunca deja el archivo destino a medio escribir; en
  el peor caso queda el `.tmp` huérfano, nunca un `.cargo3d` corrupto.
- **Backup automático**: antes de sobrescribir un archivo existente,
  `save` llama a `backup(path)`, que copia el contenido actual a
  `<archivo>.cargo3d.bak` (una sola generación, no un historial). Si el
  archivo no existía todavía (primer guardado), no hay nada que
  respaldar y `backup` devuelve `None`.
- **`created_at` conservado**: si no se pasa explícitamente, `save`
  intenta leer el `created_at` del archivo anterior (si existe) antes
  de sobrescribirlo; si ese archivo anterior está corrupto, no bloquea
  el guardado — simplemente usa la fecha actual. `MainWindow` guarda el
  valor devuelto para reutilizarlo en guardados posteriores de la misma
  sesión, sin tener que releer el archivo cada vez.
- **`validate`** hace la comprobación estructural (formato, versión de
  esquema, campos requeridos del sobre) sin reconstruir el `CargoProject`
  completo — más barato que `load` cuando solo hace falta saber si un
  archivo se puede abrir.
- **`load`** hace `validate` y además reconstruye el `CargoProject`
  completo llamando a `serialization.cargo_project_from_dict`. Cualquier
  excepción de `json`, `KeyError`/`TypeError`/`ValueError` al leer un
  campo, o `DomainValidationError`/`DuplicateSkuError` al reconstruir
  las entidades, se traduce en `ProjectFileCorruptError` — nunca se
  propaga una excepción sin tipar hacia `MainWindow`.

### Jerarquía de errores (`exceptions.py`)

```
ProjectFileError
├── ProjectFileNotFoundError      # la ruta no existe
├── ProjectFileCorruptError       # JSON inválido, formato/campos incorrectos, datos de dominio inválidos
├── UnsupportedSchemaVersionError # schema_version que esta versión no sabe leer
└── ProjectFileWriteError         # fallo de E/S al escribir o respaldar
```

`MainWindow` captura siempre `ProjectFileError` (la base) y muestra un
`QMessageBox.critical` con el mensaje — nunca deja una excepción sin
capturar llegar al usuario como un traceback.

## 4. `presentation_state`: el desacoplo entre capas

`infrastructure/persistence` no sabe nada de Qt, temas, splitters ni
docks: `presentation_state` es, para esa capa, un
`Mapping[str, Any]` que se serializa y deserializa tal cual, sin
interpretarlo. Es exactamente el mismo principio de desacoplo que ya
se usó en el visor 3D (ADR-0011): la capa de más abajo nunca conoce los
detalles de la de arriba.

Quien construye e interpreta el contenido de `presentation_state` es
`MainWindow`:

- `result_stale: bool` — si el último `PackingResult` guardado ya no
  refleja el estado actual del proyecto (ver sección 6).
- `ui_state: dict` — `theme` (`"light"`/`"dark"`), `splitters` (estado
  de cada `QSplitter.saveState()` codificado en base64, porque
  `QByteArray` no es JSON-serializable directamente), `docks_visible`
  (booleanos por nombre de dock).

## 5. Ciclo de vida completo en `MainWindow`

- **Nuevo proyecto** / **Cerrar proyecto**: piden confirmación si hay
  cambios sin guardar (sección 7), luego vacían la tabla de productos,
  el formulario de espacio, los paneles de resultados y el visor, y
  generan un nuevo `id` de proyecto.
- **Abrir**: pide confirmación si hay cambios sin guardar, `QFileDialog`
  filtrado a `*.cargo3d`, y delega en `_open_project_from_path`, que:
  1. Llama a `ProjectFileRepository.load`.
  2. Vuelca el `LoadingSpace` en el formulario
     (`LoadingSpaceFormPanel.set_loading_space`, siempre en modo
     "Personalizado" — un espacio guardado no tiene por qué coincidir
     con ningún perfil predefinido).
  3. Vuelca los `LoadUnit` en la tabla
     (`ProductTableModel.set_load_units`).
  4. Si había un `PackingResult`, lo muestra en el panel de resultados,
     la tabla de no cargados, los avisos y el visor 3D — exactamente
     con el mismo camino que usa una optimización recién terminada
     (`_populate_results` + `Packing3DViewer.display_result`).
  5. Restaura `result_stale` y el `ui_state` (tema, splitters, docks).
  6. Añade la ruta a la lista de recientes y marca el proyecto como
     "sin cambios".
- **Guardar** / **Guardar como**: construyen un `CargoProject` a partir
  del estado actual de los paneles (rechaza con `QMessageBox.warning`
  si el espacio de carga no es válido o hay SKU duplicados), llaman a
  `ProjectFileRepository.save`, y marcan el proyecto como "sin
  cambios". "Guardar" sin una ruta previa se comporta como "Guardar
  como". El nombre del proyecto es el nombre del archivo (sin
  extensión) — no existe todavía un cuadro de "nombre de proyecto"
  independiente del archivo, mismo criterio que la mayoría de
  aplicaciones de un solo documento.
- **Proyectos recientes**: submenú en Archivo, hasta 10 rutas
  (`AppSettings.recent_project_files`/`add_recent_project_file`, en
  `QSettings`). Se reconstruye cada vez que se abre el menú
  (`aboutToShow`), eliminando automáticamente las rutas que ya no
  existen en disco.

## 6. Invalidación automática del resultado

Cuando el usuario modifica productos o el espacio de carga **después**
de haber calculado un resultado, ese resultado se marca como
desactualizado — nunca se vuelve a ejecutar el algoritmo
automáticamente:

> "El resultado anterior fue invalidado porque el proyecto cambió."

Este mensaje aparece en el panel de resultados (etiqueta de aviso),
en la barra de estado y en el registro. El resultado sigue mostrándose
(no se borra: sigue siendo información real, solo que ya no coincide
con los datos actuales) hasta que el usuario ejecuta una nueva
optimización, momento en el que el aviso desaparece.

No existe todavía un panel de configuración de reglas de negocio (las
reglas de `rules` son fijas en esta fase, sin controles de usuario), así
que hoy solo productos y espacio disparan la invalidación; el mismo
mecanismo (`_on_project_data_changed`) se aplicaría sin cambios a un
futuro panel de reglas.

## 7. Cambios sin guardar

`MainWindow` rastrea un estado "sucio" (`_is_dirty`) que se activa al
editar productos, el espacio de carga, o al terminar una optimización
nueva (un resultado nuevo es un dato no guardado). El título de la
ventana muestra un `*` mientras haya cambios sin guardar
(`CargoOptimizer3D v0.10.0 — mi_proyecto*`).

Cerrar la ventana, crear un proyecto nuevo, abrir otro proyecto o abrir
uno de la lista de recientes, todos pasan primero por
`_confirm_discard_unsaved_changes`, que pregunta
Guardar/Descartar/Cancelar solo si hay cambios pendientes — si no los
hay, continúa sin interrumpir al usuario.

## 8. Migraciones (infraestructura preparada, sin versiones futuras)

Solo existe la versión de esquema `"1.0"` hoy.
`_ensure_supported_schema_version` en `project_file_repository.py` es
el único punto de extensión: cuando exista una versión `"1.1"`, ese
conjunto de versiones soportadas crece y se encadena una función de
migración real (`data 1.0 -> data 1.1`) antes de reconstruir el
proyecto. Un archivo con una versión no reconocida (más nueva que la
que la aplicación soporta) falla con `UnsupportedSchemaVersionError`
con un mensaje claro ("actualiza la aplicación"), nunca con un intento
silencioso de adivinar el formato.

## 9. Hallazgo real durante esta fase

`LoadingSpaceFormPanel.build_loading_space()` leía `category`/
`door_position` directamente de `QComboBox.currentData()` y los pasaba
tal cual a `LoadingSpace(...)`. Los enums de dominio
(`LoadingSpaceCategory`, `DoorPosition`) son `StrEnum` — subclases de
`str` — y Qt, al pasar esos valores por `QVariant` para guardarlos como
datos de un ítem de combo, los aplana a `str` planos: `currentData()`
devolvía un string igual en valor pero **sin ser la instancia del
enum**. Mientras nadie llamaba a `.value` sobre ese campo, el bug era
invisible (Python no distingue en la mayoría de operaciones); la
primera vez que algo necesitó de verdad `LoadingSpaceCategory.value`
(la serialización JSON de esta fase) lo expuso con un
`AttributeError: 'str' object has no attribute 'value'`. Corregido
envolviendo explícitamente el valor devuelto
(`LoadingSpaceCategory(self._category_combo.currentData())`,
`DoorPosition(self._door_combo.currentData())`) — un enum de Python
acepta tanto su propio miembro como el valor string equivalente, así
que la corrección es válida tanto si Qt devuelve el enum intacto como
si lo aplana.

## 10. Pruebas

- `tests/infrastructure/persistence/test_serialization.py` (10): cada
  función `_to_dict`/`_from_dict` hace un round-trip fiel, sin Qt.
- `tests/infrastructure/persistence/test_project_file_repository.py`
  (25): round-trip completo (con y sin resultado), `presentation_state`
  como blob opaco, `created_at` conservado entre guardados, backup
  automático (incluido el caso "no hay nada que respaldar"), escritura
  atómica (sin archivos `.tmp` huérfanos), archivo inexistente, JSON
  corrupto, campos faltantes, `format_name` incorrecto, versión de
  esquema futura, datos de dominio inválidos dentro de un archivo por
  lo demás bien formado, y `validate` sin reconstrucción completa.
- `tests/presentation/desktop/test_main_window_project_persistence.py`
  (23): título con `*`, invalidación de un resultado al editar
  productos/espacio, guardar (archivo real en disco, marca "sin
  cambios", añade a recientes), abrir (restaura productos, espacio,
  resultado, panel de resultados, visor — con `monkeypatch` sobre
  `viewer_widget.display_result` para verificar que recibe el
  `PackingResult` correcto sin depender de renderizado real), abrir sin
  resultado previo, ejecutar una optimización nueva limpia el aviso de
  desactualizado, el estado "desactualizado" sobrevive a un ciclo
  guardar→abrir, nuevo/cerrar proyecto reinician todo el estado,
  confirmación de cambios sin guardar (Guardar/Descartar/Cancelar,
  incluido bloquear el cierre de la ventana), menú de recientes
  (lista y elimina rutas borradas), archivo corrupto al abrir (muestra
  error, no rompe la ventana), guardar con espacio de carga inválido.

Una red de seguridad a nivel de `conftest.py`
(`_no_blocking_question_dialog`, `autouse=True`) sustituye
`QMessageBox.question` por una respuesta "Descartar" por defecto en
toda la suite de `presentation/desktop`, para que ninguna prueba pueda
colgarse esperando un diálogo real bajo la plataforma `offscreen`;
cualquier prueba que necesite otra respuesta la sobrescribe
localmente con su propio `monkeypatch`.

## 11. Limitaciones conocidas / mejoras futuras

Ver también "Mejoras futuras" al final de esta fase en el mensaje de
commit/CHANGELOG. Resumen:

- Un solo nivel de backup (`.cargo3d.bak`), no un historial de
  versiones — suficiente para "no perder el guardado anterior si algo
  sale mal", no un sistema de versionado completo.
- El nombre del proyecto es el nombre del archivo; no hay todavía un
  cuadro de diálogo de "Propiedades del proyecto" para editar nombre y
  notas independientemente del nombre de archivo (la acción
  `action_project_properties` sigue siendo un stub).
- No hay importación/exportación de/hacia otros formatos (eso es fase
  8, reportes/Excel/PDF).
- No hay control de versiones ni resolución de conflictos si dos
  personas editan el mismo archivo (fuera de alcance: esta fase asume
  un único usuario por proyecto, como pide el encargo).
