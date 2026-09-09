@echo off
setlocal
REM 0. Ensure previous instance is stopped
call "%~dp0stop_indicator.bat" >nul 2>&1
REM 1. Check pythonw.exe in PATH
where pythonw.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw.exe "%~dp0top_indicator.py"
    goto :eof
)

REM 2. Check CONDA_PREFIX
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\pythonw.exe" (
        start "" "%CONDA_PREFIX%\pythonw.exe" "%~dp0top_indicator.py"
        goto :eof
    )
)

REM 3. Fallback to python.exe
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" python.exe "%~dp0top_indicator.py"
    goto :eof
)

start "" python "%~dp0top_indicator.py"
