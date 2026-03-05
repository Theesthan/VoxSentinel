@echo off
title VoxSentinel Dashboard 5173
color 0B
cd /d "c:\\Users\\thees\\Desktop\\Eko\\Eko\\VoxSentinel\\services\\dashboard"
echo.
echo  ====================================================
echo   VoxSentinel - Dashboard
echo  ====================================================
echo.
if exist "node_modules" goto :skip_install
echo  Installing dependencies...
call npm install
echo.
:skip_install
echo  Dashboard : http://localhost:5173
echo  Auth page : http://localhost:5173/auth
echo  Make sure start-api.bat is running on 8011
echo.
start "" "http://localhost:5173"
call npm run dev
