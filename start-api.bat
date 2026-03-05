@echo off
title VoxSentinel API [:8011]
color 0A
cd /d "%~dp0"

:: Self-elevate for service start
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting admin rights to start services...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo  ============================================================
echo   VoxSentinel - API Server
echo  ============================================================
echo.

:: Add Deno to PATH (yt-dlp JS challenge solver)
set "PATH=%USERPROFILE%\.deno\bin;%PATH%"

:: Start PostgreSQL
echo  [1/4] PostgreSQL...
sc query postgresql-x64-18 | findstr "RUNNING" >nul 2>&1
if errorlevel 1 (
    net start postgresql-x64-18 >nul 2>&1
    echo         Started PostgreSQL.
) else (
    echo         Already running.
)

:: Start Redis
echo  [2/4] Redis...
sc query Redis | findstr "RUNNING" >nul 2>&1
if errorlevel 1 (
    net start Redis >nul 2>&1
    echo         Started Redis.
) else (
    echo         Already running.
)

timeout /t 2 /nobreak >nul

:: Load .env variables
echo  [3/4] Loading .env...
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" (
        echo %%a | findstr /b /c:"#" >nul || set "%%a=%%b"
    )
)
echo         Done.

:: Activate venv
echo  [4/4] Starting uvicorn on :8011...
echo.
echo  ------------------------------------------------------------
echo   API ready at  : http://localhost:8011
echo   Swagger UI    : http://localhost:8011/docs
echo   Health check  : http://localhost:8011/health
echo  ------------------------------------------------------------
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

cd services\api\src
python -m uvicorn api.main:app --host 0.0.0.0 --port 8011 --reload

pause
