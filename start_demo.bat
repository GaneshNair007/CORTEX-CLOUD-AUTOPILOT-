@echo off
title CORTEX Cloud Autopilot - Live Demo Runner
echo =====================================================================
echo   STARTING CORTEX CLOUD AUTOPILOT - BULLETPROOF DEMO RUNNER
echo =====================================================================
echo.
cd /d "%~dp0"

echo [1/3] Starting FastAPI Backend on http://127.0.0.1:8000...
start "CORTEX Backend" cmd /k "python -m uvicorn backend.api_server:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak > nul

echo [2/3] Starting Frontend Dev Console on http://localhost:3100...
cd frontend
start "CORTEX Frontend" cmd /k "npm run dev"

timeout /t 3 /nobreak > nul

echo [3/3] Opening CORTEX Console in Browser...
start http://localhost:3100/#/console

echo.
echo =====================================================================
echo   CORTEX IS LIVE!
echo   Frontend: http://localhost:3100/#/console
echo   Backend:  http://127.0.0.1:8000
echo   Admin Token: tSPT9JAFh9SHxCeB-83y_Y1t3PRg3ZQO9n8fSgTiu68
echo =====================================================================
echo Press any key to exit this launcher window (services keep running).
pause > nul
