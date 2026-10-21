@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open-dashboard.ps1"
echo.
timeout /t 3 >nul
