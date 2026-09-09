@echo off
setlocal
:: 1. 优先使用当前环境 PATH 中的 pythonw.exe (无控制台黑框)
where pythonw.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw.exe "%~dp0top_indicator.py"
    goto :eof
)

:: 2. 检查当前激活的 Conda 虚拟环境
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\pythonw.exe" (
        start "" "%CONDA_PREFIX%\pythonw.exe" "%~dp0top_indicator.py"
        goto :eof
    )
)

:: 3. 回退使用 python.exe
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" python.exe "%~dp0top_indicator.py"
    goto :eof
)

start "" python "%~dp0top_indicator.py"
