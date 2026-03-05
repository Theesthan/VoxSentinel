@echo off
title VoxSentinel Cloudflare Tunnels
echo.
echo  =====================================================
echo   VoxSentinel -- Cloudflare Quick Tunnels
echo  =====================================================
echo.
echo  How it works:
echo    - Dashboard tunnel (port 5173) is the ONLY URL you need to share.
echo    - Vite dev server automatically proxies /api calls to localhost:8011
echo      so external users' API calls work through the dashboard URL.
echo    - WebSocket (/ws) is also proxied through the same tunnel.
echo.
echo  Opening dashboard tunnel...
echo.

start "VoxSentinel Dashboard Tunnel [:5173]" cmd /k "echo Waiting for URL... && echo. && cloudflared tunnel --url http://localhost:5173 2>&1"

echo  Done! Look at the new window for a URL like:
echo    https://xxxx-xxxx-xxxx.trycloudflare.com
echo.
echo  That URL is your shareable hosted link.
echo  Share it with anyone -- no port forwarding needed.
echo.
pause
