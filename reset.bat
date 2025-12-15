@echo off
chcp 65001 >nul
title Investidubh - Reset

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║           ⚠️  INVESTIDUBH - Factory Reset                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo WARNING: This will DELETE all data including:
echo   - All investigations
echo   - All collected artifacts
echo   - All user accounts
echo   - All extracted intelligence
echo.

set /p confirm="Are you sure? Type 'YES' to confirm: "
if /i not "%confirm%"=="YES" (
    echo.
    echo Reset cancelled.
    pause
    exit /b 0
)

echo.
cd /d "%~dp0"

echo Stopping services...
docker-compose down -v

echo.
echo ✅ Reset complete. All data has been deleted.
echo.
echo Run start.bat to restart with a fresh database.
echo.
pause
