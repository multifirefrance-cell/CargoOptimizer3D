# ADR-0013: Empaquetado Windows (PyInstaller onedir + Inno Setup)

## Estado

Aceptada — 2026-07-17

## Contexto

CargoOptimizer3D Beta 1.0 (`1.0.0b2`) es hoy un proyecto Python que
solo puede ejecutarse con `python -m cargo_optimizer` dentro de un
entorno virtual. El objetivo de esta fase (ver `CLAUDE.md`, sección
"Fases del proyecto") es exclusivamente convertirlo en una aplicación
Windows instalable y ejecutable con doble clic, sin tocar
`domain`/`geometry`/`rules`/`optimization`/`application`, sin nuevas
funcionalidades y sin rediseñar la interfaz. No reabre ninguna
decisión de arquitectura anterior: solo añade la capa de distribución
que faltaba.

El árbol de dependencias incluye PySide6, PyVista/PyVistaQt (sobre
VTK), ReportLab, openpyxl y SQLAlchemy/SQLite — un perfil de
dependencias con bibliotecas nativas voluminosas (especialmente VTK:
cientos de módulos `vtkmodules.*`), no un script Python simple.

## Decisión 1: PyInstaller como herramienta de empaquetado

Se evaluó PyInstaller frente a Nuitka y cx_Freeze. Se elige
**PyInstaller** porque:

- Tiene soporte de terceros ya maduro para PySide6 y VTK/PyVista vía
  `pyinstaller-hooks-contrib` (hooks estándar para
  `vtkmodules.*`, `PySide6.Qt*`, `sqlalchemy`, `matplotlib`,
  `reportlab`, `openpyxl`), reduciendo drásticamente los
  `hiddenimports` manuales necesarios frente a Nuitka, donde el
  soporte de VTK es experimental.
- Es la herramienta con más precedente documentado para exactamente
  esta combinación (PySide6 + VTK), lo que reduce el riesgo de pasar
  la fase completa depurando problemas de empaquetado no relacionados
  con el objetivo real de la fase.
- **`pyinstaller` se declara únicamente en
  `[project.optional-dependencies].dev`** de `pyproject.toml`, nunca en
  `dependencies` — es una herramienta del entorno de desarrollo que
  construye el artefacto distribuible, no una dependencia en tiempo de
  ejecución del propio `CargoOptimizer3D.exe` generado (decisión
  explícita del propietario del proyecto).

## Decisión 2: modo `onedir`, no `onefile`

`onefile` empaqueta todo en un único `.exe` que se autoextrae a un
directorio temporal (`%TEMP%\_MEIxxxxxx`) en **cada arranque**. Con
VTK (cientos de bibliotecas nativas `.pyd`/`.dll`) esto es lento en
cada inicio y añade una superficie de fallo adicional (extracción
parcial, antivirus interceptando la escritura en `%TEMP%`, limpieza
incompleta tras un cierre anómalo). `onedir` deja todas las
bibliotecas nativas ya presentes junto al `.exe` en la carpeta de
instalación: arranque más rápido y más predecible, al coste de una
carpeta de distribución más grande en disco (ver tamaño medido en el
informe final) — coste aceptable para una aplicación de escritorio
instalada una vez, no para un script de un solo uso.

## Decisión 3: resolución de rutas de recursos compatible con código fuente y build congelado

`icons.py` era el único punto de `src/` que resolvía una ruta de
recurso con `Path(__file__).parent` (confirmado por búsqueda exhaustiva
en todo `src/cargo_optimizer/`). Bajo PyInstaller, los módulos `.py` se
empaquetan comprimidos dentro de un archivo `PYZ`, no como archivos
sueltos en disco: `__file__` de un módulo congelado no es una ruta
fiable para localizar recursos que sí se copiaron tal cual (SVGs de
`resources/icons/`).

Se introduce `presentation/desktop/paths.py::presentation_desktop_root()`,
que usa el mecanismo oficial de PyInstaller (`sys._MEIPASS`, que en
modo `onedir` apunta al propio directorio de la distribución, no a un
directorio temporal) cuando existe, y cae a `Path(__file__).parent` en
caso contrario — comportamiento idéntico en ambos entornos desde el
punto de vista de quien llama. No se generaliza esto a un mecanismo de
recursos más amplio (no hay pipeline `.qrc`, no hay un `ResourceLoader`
genérico): es la corrección mínima y puntual del único caso real
existente, siguiendo la misma disciplina de "no sobrearquitecturar" ya
aplicada en el resto del proyecto.

Ningún otro punto del código necesitó cambios: `get_user_database_path()`
(`infrastructure/database/paths.py`) ya resolvía
`%LOCALAPPDATA%/CargoOptimizer3D` de forma independiente de
`sys.frozen`, y `AppSettings` (`presentation/desktop/settings.py`) ya
usaba `QSettings(ORGANIZATION_NAME, APPLICATION_NAME)` sin formato
explícito, que en Windows resuelve al registro
(`HKEY_CURRENT_USER\Software\CargoOptimizer3D\CargoOptimizer3D`) —
ninguno de los dos depende de la ubicación del ejecutable ni del
directorio de trabajo.

## Decisión 4: Inno Setup para el instalador

Se elige Inno Setup (`.iss` compilado con `ISCC.exe`) frente a MSI/WiX
por preferencia explícita del propietario del proyecto y por ser
suficiente para los requisitos de esta fase: instalación en
`Program Files`, accesos directos de Escritorio y Menú Inicio,
desinstalador registrado en "Agregar o quitar programas", y
preservación de los datos de usuario (`%LOCALAPPDATA%/CargoOptimizer3D`)
al actualizar o desinstalar salvo confirmación explícita del usuario en
el propio flujo de desinstalación. No se introduce firma digital,
autoactualizador, licencia, activación ni telemetría en esta fase — ver
`CLAUDE.md`, lista explícita de "no implementar todavía".

## Consecuencias

**Beneficios:**

- Un usuario Beta puede instalar y ejecutar CargoOptimizer3D sin
  Python, sin entorno virtual y sin terminal — el objetivo único de la
  fase.
- El build es reproducible con un único comando
  (`scripts\build_windows_beta.bat`) y un único archivo `.spec`
  versionado (`packaging/CargoOptimizer3D.spec`), sin pasos manuales.
- Ninguna capa de negocio (`domain`/`geometry`/`rules`/`optimization`/
  `application`) se modificó; el único cambio de código en `src/` es la
  resolución de rutas de recursos ya descrita en la Decisión 3.

**Costes / riesgos aceptados:**

- La carpeta de distribución `onedir` es considerablemente más grande
  que el código fuente (VTK domina el tamaño) — ver cifra exacta en el
  informe final de esta fase.
- PyInstaller no ofrece firma digital ni actualización automática por
  sí mismo: el instalador generado hoy no está firmado (Windows
  SmartScreen puede advertir al usuario Beta la primera vez) — aceptado
  explícitamente como fuera de alcance de esta fase.
- Cualquier nueva dependencia nativa futura (una versión distinta de
  VTK, una biblioteca adicional con extensiones C) puede requerir
  revisar `hiddenimports`/`datas` en `packaging/CargoOptimizer3D.spec`
  — es un coste de mantenimiento inherente a empaquetar bibliotecas
  nativas con PyInstaller, no específico de esta decisión frente a las
  alternativas evaluadas.
