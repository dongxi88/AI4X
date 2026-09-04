@echo off
echo Stopping Anti-Lock processes...
powershell.exe -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*anti-lock-screen-v2.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped PID: ' + $_.ProcessId) }"
echo Done!
timeout /t 2 >nul