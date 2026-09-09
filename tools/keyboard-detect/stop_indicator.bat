@echo off
setlocal
:: 1. 优先使用当前环境 PATH 中的 python.exe
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python.exe "%~dp0top_indicator.py" --stop
    goto :eof
)

:: 2. 检查当前激活的 Conda 虚拟环境
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        "%CONDA_PREFIX%\python.exe" "%~dp0top_indicator.py" --stop
        goto :eof
    )
)

python "%~dp0top_indicator.py" --stop
