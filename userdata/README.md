# userdata/

Destino por defecto de todo dato generado por el usuario en tiempo de
ejecución: proyectos guardados, planes de carga exportados, reportes
generados, bases de datos locales. Nada de lo que se genere aquí se
versiona en git (ver `.gitignore`): es contenido del usuario, no
código fuente.

Esta carpeta aparece vacía en el repositorio a propósito: la
persistencia de proyectos (`.cargo3d`, fase 7.0) y la generación de
informes (Excel desde fase 8.0, PDF desde fase 9.1) ya existen y
escriben aquí por defecto — lo que está vacío es únicamente el
directorio versionado en git, no la funcionalidad. El catálogo SQLite
(fase 7.1) no vive aquí: se guarda en
`%LOCALAPPDATA%/CargoOptimizer3D/` (ver `docs/Database.md`).
