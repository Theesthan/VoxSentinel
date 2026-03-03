@echo off
title VoxSentinel YouTube Media Worker
echo.
echo  ============================================
echo   VoxSentinel YouTube Media Worker
echo  ============================================
echo.

:: Check for Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check for yt-dlp
where yt-dlp >nul 2>&1
if errorlevel 1 (
    echo [WARNING] yt-dlp not found. Installing...
    pip install yt-dlp
)

:: Check for FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg not found. Please install FFmpeg and add to PATH.
    echo           Download from https://ffmpeg.org/download.html
    echo.
)

:: Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q

:: Set defaults if not already set
if not defined WORKER_PORT set WORKER_PORT=8787
if not defined WORKER_SECRET set WORKER_SECRET=

echo.
echo [2/2] Starting worker on port %WORKER_PORT%...
echo.
echo  To connect Railway to this worker, set these env vars on Railway:
echo    YT_WORKER_URL = http://YOUR_PUBLIC_IP:%WORKER_PORT%
echo    YT_WORKER_SECRET = %WORKER_SECRET%
echo.
echo  Make sure port %WORKER_PORT% is open in your firewall/router.
echo.

python worker.py

pause
