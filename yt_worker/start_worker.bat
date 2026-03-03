@echo off
title VoxSentinel YouTube Media Worker
echo.
echo  ============================================
echo   VoxSentinel YouTube Media Worker
echo  ============================================
echo.

:: Move to the script's own directory so relative paths always work
cd /d "%~dp0"

:: ── 1. Check Python ───────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: ── 2. Create venv if it doesn't exist yet ────────────────────────
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    :: Remove any stale marker so deps are installed fresh
    if exist ".deps_installed" del ".deps_installed"
)

set PYTHON=venv\Scripts\python.exe
set PIP=venv\Scripts\pip.exe

:: ── 3. Install dependencies only once (skip if marker exists) ─────
if not exist ".deps_installed" (
    echo [2/3] Installing dependencies into venv (first run only)...
    %PIP% install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    :: Save marker so we skip this next time
    echo installed > .deps_installed
) else (
    echo [2/3] Dependencies already installed. Skipping.
)

:: ── 4. Verify yt-dlp (Python import, not PATH check) ─────────────
%PYTHON% -c "import yt_dlp" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] yt-dlp import failed. Re-installing...
    %PIP% install yt-dlp -q
    del ".deps_installed" 2>nul
)

:: ── 5. Warn if FFmpeg is missing ──────────────────────────────────
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg not found in system PATH.
    echo           Download from https://ffmpeg.org/download.html and add to PATH.
    echo.
)

:: ── 6. Load .env if present ───────────────────────────────────────
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
    )
)

:: Set defaults if still not set
if not defined WORKER_PORT set WORKER_PORT=8787
if not defined WORKER_SECRET set WORKER_SECRET=

echo.
echo [3/3] Starting worker on port %WORKER_PORT%...
echo.
echo  To connect Railway to this worker, set these env vars on Railway:
echo    YT_WORKER_URL    = http://YOUR_PUBLIC_IP:%WORKER_PORT%
echo    YT_WORKER_SECRET = %WORKER_SECRET%
echo.
echo  Make sure port %WORKER_PORT% is open in your firewall/router.
echo.

%PYTHON% worker.py

pause
