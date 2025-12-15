@echo off
chcp 65001 >nul
title Investidubh - Stop

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           🔍 INVESTIDUBH - Stopping Services                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo Stopping all services...
docker-compose down

echo.
echo ✅ All services stopped.
echo.
echo To restart: Run start.bat
echo.
pause
