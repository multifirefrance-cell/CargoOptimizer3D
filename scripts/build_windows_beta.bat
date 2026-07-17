@echo off
REM Reconstruye el build "onedir" de CargoOptimizer3D Beta con PyInstaller.
REM Un unico comando, reproducible: limpia builds previos, construye,
REM y verifica que el ejecutable resultante exista.
REM Uso: scripts\build_windows_beta.bat  (desde la raiz del repo)

setlocal
cd /d "%~dp0.."

echo === CargoOptimizer3D - build Windows Beta ===

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: no se encontro .venv\Scripts\python.exe. Crea el entorno virtual primero.
    exit /b 1
)

echo.
echo [1/3] Limpiando builds anteriores...
if exist "build\CargoOptimizer3D" rmdir /s /q "build\CargoOptimizer3D"
if exist "dist\CargoOptimizer3D" rmdir /s /q "dist\CargoOptimizer3D"

echo.
echo [2/3] Generando el icono de la aplicacion...
".venv\Scripts\python.exe" "packaging\generate_app_icon.py"
if errorlevel 1 (
    echo ERROR: fallo la generacion del icono.
    exit /b 1
)

echo.
echo [2.5/3] Ejecutando PyInstaller (modo onedir)...
".venv\Scripts\pyinstaller.exe" "packaging\CargoOptimizer3D.spec" --noconfirm --clean
if errorlevel 1 (
    echo ERROR: fallo la construccion con PyInstaller.
    exit /b 1
)

echo.
echo [3/3] Verificando el resultado...
if not exist "dist\CargoOptimizer3D\CargoOptimizer3D.exe" (
    echo ERROR: no se genero dist\CargoOptimizer3D\CargoOptimizer3D.exe
    exit /b 1
)

echo.
echo Build completo: dist\CargoOptimizer3D\CargoOptimizer3D.exe
endlocal
