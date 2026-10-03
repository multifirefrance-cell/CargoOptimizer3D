@echo off
setlocal EnableDelayedExpansion
title CargoOptimizer3D

:: ================================================================
:: DIRECTORIO DEL PROYECTO (donde esta este .bat = carpeta OneDrive)
:: Funciona en cualquier PC sin importar la ruta de OneDrive.
:: ================================================================
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: ================================================================
:: OPCION 1: usar el venv que ya esta dentro del proyecto (si es valido)
:: ================================================================
set "PROJECT_VENV_PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
if exist "%PROJECT_VENV_PYTHON%" (
    "%PROJECT_VENV_PYTHON%" --version >nul 2>&1
    if not errorlevel 1 (
        echo Abriendo CargoOptimizer3D...
        "%PROJECT_VENV_PYTHON%" -m cargo_optimizer
        goto :end
    )
)

:: ================================================================
:: OPCION 2: venv LOCAL a esta maquina (NO en OneDrive)
:: Se usa cuando el venv del proyecto no funciona (otra maquina).
:: ================================================================
set "VENV_DIR=%LOCALAPPDATA%\CargoOptimizer3D\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ----------------------------------------------------------------
:: BUSCAR PYTHON instalado en esta maquina
:: ----------------------------------------------------------------
set "PYTHON_EXE="
for %%V in (3.13 3.12 3.11) do (
    if not defined PYTHON_EXE (
        py -%%V --version >nul 2>&1
        if not errorlevel 1 set "PYTHON_EXE=py -%%V"
    )
)
if not defined PYTHON_EXE (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py"
)
if not defined PYTHON_EXE (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    echo.
    echo ERROR: No se encontro Python en este equipo.
    echo Instale Python 3.12 o superior desde https://python.org
    echo.
    pause
    exit /b 1
)

:: ----------------------------------------------------------------
:: CREAR VENV + INSTALAR DEPENDENCIAS (solo la primera vez)
:: ----------------------------------------------------------------
if not exist "%VENV_PYTHON%" (
    echo.
    echo  Primera ejecucion en este equipo. Configurando entorno...
    echo  Esto puede tardar 5-10 minutos. No cierre esta ventana.
    echo.
    if not exist "%LOCALAPPDATA%\CargoOptimizer3D" mkdir "%LOCALAPPDATA%\CargoOptimizer3D"

    %PYTHON_EXE% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause & exit /b 1
    )

    "%VENV_PIP%" install --upgrade pip --quiet --disable-pip-version-check
    "%VENV_PIP%" install -e "%PROJECT_DIR%" --quiet
    if errorlevel 1 (
        echo.
        echo ERROR: Fallo la instalacion de dependencias.
        echo Verifique su conexion a internet e intente de nuevo.
        echo Para reintentar, elimine la carpeta:
        echo   %VENV_DIR%
        pause & exit /b 1
    )
    echo  Instalacion completada.
    echo.
)

:: ----------------------------------------------------------------
:: CREAR ACCESO DIRECTO EN EL ESCRITORIO de esta maquina
:: ----------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desk = (New-Object -Com WScript.Shell).SpecialFolders('Desktop');" ^
    "$lnk = Join-Path $desk 'CargoOptimizer3D.lnk';" ^
    "if (-not (Test-Path $lnk)) {" ^
        "$s = (New-Object -Com WScript.Shell).CreateShortcut($lnk);" ^
        "$s.TargetPath = '%~f0';" ^
        "$s.WorkingDirectory = '%PROJECT_DIR%';" ^
        "$s.Description = 'CargoOptimizer3D';" ^
        "$ico = '%PROJECT_DIR%\packaging\app_icon.ico';" ^
        "if (Test-Path $ico) { $s.IconLocation = $ico };" ^
        "$s.Save() }" >nul 2>&1

:: ----------------------------------------------------------------
:: LANZAR EL PROGRAMA
:: ----------------------------------------------------------------
echo  Abriendo CargoOptimizer3D...
"%VENV_PYTHON%" -m cargo_optimizer

:end
if errorlevel 1 (
    echo.
    echo El programa cerro con un error.
    pause
)
endlocal
