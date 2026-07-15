# Ejemplos

Proyectos y scripts de ejemplo que demuestran el uso real de
CargoOptimizer3D sobre casos concretos.

## `example_project.cargo3d`

Proyecto de ejemplo (fase 7.0): un contenedor de 20 pies con tres Load
Units representativos (una caja individual, un pallet sin apilamiento,
una caja frágil) y un `PackingResult` real calculado con
`greedy_extreme_point_v1` (24/24 unidades cargadas). Generado con el
propio `ProjectFileRepository` — no escrito a mano — para garantizar
que es un archivo `.cargo3d` válido y abrible directamente desde
CargoOptimizer3D (`Archivo → Abrir…`). Ver `docs/ProjectFiles.md` para
el detalle del formato.
