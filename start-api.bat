@echo off
cd /d "%~dp0"

:: Self-elevate to Administrator (needed to start services)
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting admin rights to start services...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Add Deno to PATH for yt-dlp JS challenge solving
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"

:: ── Start PostgreSQL ──────────────────────────────────────
sc query postgresql-x64-18 | findstr "RUNNING" >nul 2>&1
if errorlevel 1 (
    echo Starting PostgreSQL...
    net start postgresql-x64-18
) else (
    echo PostgreSQL already running.
)

:: ── Start Redis ───────────────────────────────────────────
sc query Redis | findstr "RUNNING" >nul 2>&1
if errorlevel 1 (
    echo Starting Redis...
    net start Redis
) else (
    echo Redis already running.
)

:: Give services a moment to be ready
timeout /t 2 /nobreak >nul

:: ── Load .env file ────────────────────────────────────────
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" (
        echo %%a | findstr /b /c:"#" >nul || set "%%a=%%b"
    )
)

echo.
echo Starting VoxSentinel API on http://localhost:8011
echo Dashboard: run start-dashboard.bat then open http://localhost:5173
echo.
cd services\api\src
python -m uvicorn api.main:app --host 0.0.0.0 --port 8011
