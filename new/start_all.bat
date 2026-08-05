@echo off
echo Starting GHG Platform...

echo Starting Backend (Flask)...
start "GHG Backend" cmd /k "cd server && python app.py"

echo Starting Frontend (Vite)...
start "GHG Frontend" cmd /k "cd client && npm run dev"

echo.
echo Application starting...
echo Backend:   http://localhost:5000
echo Frontend:  http://localhost:5173
echo.
echo Please wait a moment for the servers to initialize.
