# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para CargoOptimizer3D — modo `onedir` (ver ADR-0013).

Se invoca desde la raíz del repo:
    pyinstaller packaging/CargoOptimizer3D.spec --noconfirm

`onedir`, no `onefile`: VTK/PyVista cargan muchas bibliotecas nativas
en tiempo de ejecución (`vtkmodules/*.pyd`); extraerlas todas a un
directorio temporal en cada arranque (lo que hace `onefile`) es más
lento y más frágil que dejarlas ya presentes en disco junto al
ejecutable.
"""

from pathlib import Path

block_cipher = None

REPO_ROOT = Path(SPECPATH).parent
SRC_DIR = REPO_ROOT / "src"
ICON_PATH = REPO_ROOT / "packaging" / "app_icon.ico"

# Recursos de solo lectura empaquetados junto al código (ver
# `presentation/desktop/paths.py`): solo los iconos SVG existen hoy.
# Se preserva la misma ruta relativa dentro del bundle
# (`cargo_optimizer/presentation/desktop/resources/...`) para que
# `presentation_desktop_root()` los encuentre igual que en el árbol
# fuente.
datas = [
    (
        str(SRC_DIR / "cargo_optimizer" / "presentation" / "desktop" / "resources"),
        "cargo_optimizer/presentation/desktop/resources",
    ),
]

a = Analysis(
    [str(SRC_DIR / "cargo_optimizer" / "__main__.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pyvistaqt",
        "vtkmodules.all",
        "vtkmodules.util",
        "vtkmodules.util.numpy_support",
        "vtkmodules.qt.QVTKRenderWindowInteractor",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # `mypy` es una herramienta de desarrollo (lint/tipado, nunca en
    # tiempo de ejecución — ver CLAUDE.md). Se excluye explícitamente
    # porque `pyvista/typing/mypy_plugin.py` hace
    # `if importlib.util.find_spec("mypy"):` en tiempo de importación
    # (no solo bajo `TYPE_CHECKING`): si PyInstaller detecta `mypy`
    # instalado en el entorno de build, intenta empaquetarlo, pero el
    # propio `mypy` está compilado con mypyc en módulos nativos con
    # nombre hash (p. ej. `08ae81f72d5a2b5fa9e0__mypyc`) que PyInstaller
    # no resuelve automáticamente, y el arranque falla con
    # `ModuleNotFoundError`. Excluir `mypy` hace que `find_spec`
    # devuelva `None` en el build congelado, igual que en cualquier
    # máquina de usuario final sin `mypy` instalado.
    excludes=["mypy"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CargoOptimizer3D",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CargoOptimizer3D",
)
