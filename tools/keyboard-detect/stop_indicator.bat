@echo off
setlocal
REM 1. Check python.exe in PATH
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python.exe "%~dp0top_indicator.py" --stop
    goto :eof
)

REM 2. Check CONDA_PREFIX
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        "%CONDA_PREFIX%\python.exe" "%~dp0top_indicator.py" --stop
        goto :eof
    )
)

python "%~dp0top_indicator.py" --stop
