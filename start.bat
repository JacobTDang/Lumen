@echo off
setlocal

set ROOT=%~dp0

echo Starting Lumen backend...
start "Lumen — Backend" cmd /k "cd /d "%ROOT%" && call venv\Scripts\activate.bat && cd backend && python app.py"

echo Starting Lumen frontend...
start "Lumen — Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

echo Both servers launching in separate windows.
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:5173
