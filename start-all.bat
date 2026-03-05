@echo off
title VoxSentinel Launcher
color 0F
cd /d "%~dp0"

echo.
echo  ============================================================
echo   VoxSentinel - Full Stack Launcher
echo  ============================================================
echo.
echo  This will open two terminal windows:
echo    [1] API Server  - PostgreSQL + Redis + uvicorn :8011
echo    [2] Dashboard   - Vite dev server :5173
echo.
echo  After both windows are ready:
echo    Dashboard  : http://localhost:5173
echo    API Docs   : http://localhost:8011/docs
echo    API Health : http://localhost:8011/health
echo.
echo  ============================================================
echo.

:: Window 1: API
echo  [1/2] Starting API server (may prompt for admin)...
start "VoxSentinel API [:8011]" cmd /k ""%~dp0start-api.bat""

:: Give API time to get PostgreSQL + Redis up
echo  Waiting 6 s for infrastructure to start...
timeout /t 6 /nobreak >nul

:: Window 2: Dashboard
echo  [2/2] Starting dashboard dev server...
start "VoxSentinel Dashboard [:5173]" cmd /k ""%~dp0start-dashboard.bat""

echo.
echo  Both windows are opening. Watch them for any errors.
echo.
echo  ------------------------------------------------------------
echo   Dashboard  :  http://localhost:5173
echo   API Docs   :  http://localhost:8011/docs
echo  ------------------------------------------------------------
echo.
echo  To expose publicly, run:  start-tunnels.bat
echo.
pause
