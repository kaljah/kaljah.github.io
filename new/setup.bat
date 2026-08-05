@echo off
echo Setting up GHG Platform (Flask + React)...

echo.
echo [1/3] Installing Python Backend Dependencies...
cd server
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install Python dependencies. Please ensure python and pip are installed.
    pause
    exit /b
)

echo.
echo [2/3] Installing Node.js Frontend Dependencies...
cd ../client
call npm install
if %errorlevel% neq 0 (
    echo Failed to install Node dependencies. Please ensure node and npm are installed.
    pause
    exit /b
)

echo.
echo [3/3] Setup Complete!
echo.
echo To start the application, run 'start_all.bat' in the 'new' folder.
cd ..
pause
