@echo off
chcp 65001 >nul
title Investidubh Launcher

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           🔍 INVESTIDUBH - OSINT Platform                    ║
echo ║                     Launcher v2.0                            ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Check if Docker is running
echo [1/3] Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ Docker is not running!
    echo    Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)
echo      ✓ Docker is running

:: Navigate to project directory
cd /d "%~dp0"

:: Start services (without build to be faster if already built)
echo.
echo [2/3] Starting Investidubh services...
docker-compose up -d

echo.
echo [3/3] Waiting for services...
timeout /t 15 /nobreak >nul

:: Open browser regardless
echo      Opening browser...
start http://localhost:3000

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║  Investidubh starting...                                     ║
echo ║                                                              ║
echo ║  Dashboard: http://localhost:3000                            ║
echo ║  API:       http://localhost:8080                            ║
echo ║                                                              ║
echo ║  To stop: Run stop.bat                                       ║
echo ║  To view logs: Run logs.bat                                  ║
echo ║  To rebuild: docker-compose up -d --build                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
pause
