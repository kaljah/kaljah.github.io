@echo off
setlocal enableextensions
set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

if defined GHG_SANDBOX_SERVER_DIR (
    set "SERVER_DIR=%GHG_SANDBOX_SERVER_DIR%"
) else (
    set "SERVER_DIR=%REPO_ROOT%\new\server"
)

if not defined PYTHONEXE set "PYTHONEXE=python"
if not defined GHG_DB_PATH set "GHG_DB_PATH=%SERVER_DIR%\ghg_app.db"
if not defined GHG_TEMPLATE_PATH set "GHG_TEMPLATE_PATH=%SERVER_DIR%\instance\demo_template.db"

set "RESET_PW_ARG="
for %%A in (%*) do (
    if /i "%%~A"=="--reset-passwords" set "RESET_PW_ARG=--reset-passwords"
)

echo [Sandbox Reset] Server dir: %SERVER_DIR%

echo [1/3] Removing SQLite WAL/SHM sidecars and restoring pristine template DB...
if exist "%GHG_DB_PATH%-wal" del /f /q "%GHG_DB_PATH%-wal" >nul 2>&1
if exist "%GHG_DB_PATH%-shm" del /f /q "%GHG_DB_PATH%-shm" >nul 2>&1
if exist "%GHG_DB_PATH%-journal" del /f /q "%GHG_DB_PATH%-journal" >nul 2>&1

if exist "%GHG_TEMPLATE_PATH%" (
    "%PYTHONEXE%" -c "import os, pathlib, shutil; src = pathlib.Path(os.environ['GHG_TEMPLATE_PATH']); dst = pathlib.Path(os.environ['GHG_DB_PATH']); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)"
    if errorlevel 1 (
        echo Failed to restore template database from %GHG_TEMPLATE_PATH%.
        exit /b 1
    )
) else (
    echo Template DB not found at %GHG_TEMPLATE_PATH%; creating pristine template from scratch...
    "%PYTHONEXE%" "%REPO_ROOT%\scripts\seed_demo.py" --recreate --reset-passwords --db "%GHG_DB_PATH%" --template "%GHG_TEMPLATE_PATH%"
    if errorlevel 1 (
        echo Failed to create pristine template database.
        exit /b 1
    )
)

echo [2/3] Re-seeding demo database idempotently...
if defined RESET_PW_ARG (
    "%PYTHONEXE%" "%REPO_ROOT%\scripts\seed_demo.py" --db "%GHG_DB_PATH%" --reset-passwords --template "%GHG_TEMPLATE_PATH%"
) else (
    "%PYTHONEXE%" "%REPO_ROOT%\scripts\seed_demo.py" --db "%GHG_DB_PATH%"
)
if errorlevel 1 (
    echo Failed to re-seed demo database.
    exit /b 1
)

if exist "%GHG_DB_PATH%-wal" del /f /q "%GHG_DB_PATH%-wal" >nul 2>&1
if exist "%GHG_DB_PATH%-shm" del /f /q "%GHG_DB_PATH%-shm" >nul 2>&1

echo [3/3] Clearing sandbox upload staging, generated caches, and report job artifacts...
"%PYTHONEXE%" -c "import os, pathlib, shutil; s = pathlib.Path(os.environ['SERVER_DIR']); dirs = [s/'upload_jobs', s/'uploads', s/'instance'/'uploads', s/'instance'/'chart_cache', s/'instance'/'master_report_jobs', s/'report_jobs', s/'tmp']; [shutil.rmtree(item, ignore_errors=True) if item.is_dir() else item.unlink(missing_ok=True) for d in dirs if d.exists() for item in d.iterdir() if item.name != '.gitkeep']"
if errorlevel 1 (
    echo Failed to clear sandbox upload and cache directories.
    exit /b 1
)

echo [OK] Sandbox reset complete.
exit /b 0
