@echo off
setlocal EnableDelayedExpansion
title CargoOptimizer3D Web

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: ── Usar el venv del proyecto ─────────────────────────────────────────────
set "PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo.
    echo  ERROR: No se encontro el entorno virtual en:
    echo    %PROJECT_DIR%\.venv
    echo  Ejecute primero iniciar.bat para configurar el entorno.
    echo.
    pause
    exit /b 1
)

:: ── Crear acceso directo en el Escritorio (solo la primera vez) ───────────
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$desk = (New-Object -Com WScript.Shell).SpecialFolders('Desktop');" ^
    "$lnk  = Join-Path $desk 'CargoOptimizer3D Web.lnk';" ^
    "if (-not (Test-Path $lnk)) {" ^
        "$s = (New-Object -Com WScript.Shell).CreateShortcut($lnk);" ^
        "$s.TargetPath      = '%~f0';" ^
        "$s.WorkingDirectory = '%PROJECT_DIR%';" ^
        "$s.Description     = 'CargoOptimizer3D — interfaz web';" ^
        "$ico = '%PROJECT_DIR%\packaging\app_icon.ico';" ^
        "if (Test-Path $ico) { $s.IconLocation = $ico };" ^
        "$s.Save() }" >nul 2>&1

:: ── Lanzar servidor web (abre el navegador automaticamente) ───────────────
echo  Iniciando CargoOptimizer3D Web...
echo  El navegador se abrira en http://localhost:8080
echo.
"%PYTHON%" "%PROJECT_DIR%\run_web.py"

if errorlevel 1 (
    echo.
    echo  El servidor cerro con un error.
    pause
)
endlocal
