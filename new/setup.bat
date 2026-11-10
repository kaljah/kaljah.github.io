@echo off
setlocal enableextensions
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

if defined GHG_SANDBOX_SERVER_DIR (
    set "SERVER_DIR=%GHG_SANDBOX_SERVER_DIR%"
) else (
    set "SERVER_DIR=%SCRIPT_DIR%server"
)

if not defined PYTHONEXE set "PYTHONEXE=python"
if not defined GHG_DB_PATH set "GHG_DB_PATH=%SERVER_DIR%\ghg_app.db"
if not defined GHG_TEMPLATE_PATH set "GHG_TEMPLATE_PATH=%SERVER_DIR%\instance\demo_template.db"

set "DB_ONLY=0"
for %%A in (%*) do (
    if /i "%%~A"=="--db-only" set "DB_ONLY=1"
    if /i "%%~A"=="--no-pause" set "GHG_NO_PAUSE=1"
)

echo Setting up GHG Platform (Flask + React)...

if "%DB_ONLY%"=="0" (
    echo.
    echo [1/4] Installing Python Backend Dependencies...
    pushd "%SCRIPT_DIR%server"
    "%PYTHONEXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        popd
        echo Failed to install Python dependencies. Please ensure python and pip are installed.
        if not "%GHG_NO_PAUSE%"=="1" pause
        exit /b 1
    )
    popd

    echo.
    echo [2/4] Installing Node.js Frontend Dependencies...
    pushd "%SCRIPT_DIR%client"
    call npm install
    if errorlevel 1 (
        popd
        echo Failed to install Node dependencies. Please ensure node and npm are installed.
        if not "%GHG_NO_PAUSE%"=="1" pause
        exit /b 1
    )
    popd
) else (
    echo.
    echo [1/4 ^& 2/4] Skipping package installation ^(--db-only mode^)...
)

echo.
echo [3/4] Initializing Database Schema (Alembic) & Seeding Demo Data...
set "DB_URI_PATH=%GHG_DB_PATH:\=/%"
set "DATABASE_URL=sqlite:///%DB_URI_PATH%"
set "FLASK_ENV=development"
set "SEED_ADMIN=false"

"%PYTHONEXE%" -c "import os, pathlib; p = pathlib.Path(os.environ['GHG_DB_PATH']); p.parent.mkdir(parents=True, exist_ok=True)"
if exist "%GHG_DB_PATH%" del /f /q "%GHG_DB_PATH%" >nul 2>&1
if exist "%GHG_DB_PATH%-wal" del /f /q "%GHG_DB_PATH%-wal" >nul 2>&1
if exist "%GHG_DB_PATH%-shm" del /f /q "%GHG_DB_PATH%-shm" >nul 2>&1

pushd "%SCRIPT_DIR%server"
"%PYTHONEXE%" -m flask --app app db upgrade
if errorlevel 1 (
    popd
    echo Failed to initialize database schema via flask db upgrade.
    if not "%GHG_NO_PAUSE%"=="1" pause
    exit /b 1
)
popd

"%PYTHONEXE%" "%REPO_ROOT%\scripts\seed_demo.py" --reset-passwords --db "%GHG_DB_PATH%" --template "%GHG_TEMPLATE_PATH%"
if errorlevel 1 (
    echo Failed to seed synthetic demo database.
    if not "%GHG_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo.
echo [4/4] Setup Complete!
echo   Demo DB:     %GHG_DB_PATH%
echo   Template DB: %GHG_TEMPLATE_PATH%
echo   Save the generated demo credentials printed above.
echo   To reset the sandbox later, run 'reset_sandbox.bat' (or 'reset_sandbox.sh').
echo   To start the application, run 'start_all.bat' in the 'new' folder.
if not "%GHG_NO_PAUSE%"=="1" pause
exit /b 0
