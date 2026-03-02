@echo off
cd /d "%~dp0services\dashboard"

:: Install dependencies if node_modules is missing
if not exist "node_modules" (
    echo Installing dashboard dependencies...
    npm install
)

:: Open browser after a 3-second delay (in background)
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5173"

echo Starting VoxSentinel dashboard — opening http://localhost:5173
npm run dev
