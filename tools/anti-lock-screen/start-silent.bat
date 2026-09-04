@echo off
powershell.exe -ExecutionPolicy Bypass -Command "Start-Process powershell -WindowStyle Hidden -ArgumentList '-ExecutionPolicy Bypass -File \"\"%~dp0anti-lock-screen-v2.ps1\"\" -Silent'"