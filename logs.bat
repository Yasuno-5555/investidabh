@echo off
chcp 65001 >nul
title Investidubh - Logs

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           📋 INVESTIDUBH - Live Logs                         ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo Showing live logs from all services...
echo Press Ctrl+C to stop viewing logs.
echo.

cd /d "%~dp0"
docker-compose logs -f --tail=100
