@echo off
title Anti-Lock Screen
cls

echo ======================================================
echo          Anti-Lock Screen Launcher
echo ======================================================
echo.
echo   [1] Silent Run (Background, logs saved in logs\)
echo   [2] Debug Run  (Foreground, shows popup and console)
echo   [3] Stop Running Anti-Lock Processes
echo.
echo ======================================================
choice /c 123 /n /m "Select [1, 2, 3]: "

if errorlevel 3 goto opt3
if errorlevel 2 goto opt2
if errorlevel 1 goto opt1

:opt1
powershell.exe -ExecutionPolicy Bypass -Command "Start-Process powershell -WindowStyle Hidden -ArgumentList '-ExecutionPolicy Bypass -File \"\"%~dp0anti-lock-screen-v2.ps1\"\" -Silent'"
echo.
echo Started in background!
timeout /t 2 >nul
exit /b

:opt2
echo.
powershell.exe -ExecutionPolicy Bypass -File "%~dp0anti-lock-screen-v2.ps1"
pause
exit /b

:opt3
echo.
powershell.exe -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*anti-lock-screen-v2.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped PID: ' + $_.ProcessId) }"
echo.
pause
exit /b