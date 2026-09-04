@echo off
title Anti-Lock Screen
chcp 65001 >nul

echo ======================================================
echo       防锁屏脚本启动器 (Anti-Lock Screen)
echo ======================================================
echo 1. 后台静默运行 (推荐，无弹窗/托盘，仅记录日志)
echo 2. 前台调试运行 (显示绿色图标、Toast 通知与控制台输出)
echo 3. 停止正在运行的防锁屏进程
echo ======================================================
set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" (
    powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -WindowStyle Hidden -ArgumentList '-ExecutionPolicy Bypass -File \"\"%~dp0anti-lock-screen-v2.ps1\"\" -Silent'"
    echo 后台静默进程已启动！
    timeout /t 3 >nul
    exit
)

if "%choice%"=="2" (
    powershell -ExecutionPolicy Bypass -File "%~dp0anti-lock-screen-v2.ps1"
    pause
    exit
)

if "%choice%"=="3" (
    powershell -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { .CommandLine -like '*anti-lock-screen-v2.ps1*' } | ForEach-Object { Stop-Process -Id .ProcessId -Force; Write-Host ('已停止进程 PID: ' + .ProcessId) }"
    pause
    exit
)

echo 无效输入，退出。
pause
