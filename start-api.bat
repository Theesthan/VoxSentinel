@echo off
cd /d "%~dp0"

:: Load .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" (
        echo %%a | findstr /b /c:"#" >nul || set "%%a=%%b"
    )
)

cd services\api\src
python -m uvicorn api.main:app --host 0.0.0.0 --port 8010 --reload
