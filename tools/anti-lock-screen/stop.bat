@echo off
chcp 65001 >nul
echo 正在停止防锁屏进程...
powershell -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { .CommandLine -like '*anti-lock-screen-v2.ps1*' } | ForEach-Object { Stop-Process -Id .ProcessId -Force; Write-Host ('已终止进程 PID: ' + .ProcessId) }"
echo 完成！
timeout /t 2 >nul
