@echo off
rem ClipboardKeeper - run in foreground with live console output (for debugging)
setlocal
set "HERE=%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python.exe not found in PATH.
    echo Install Python 3.8+ and tick "Add Python to PATH".
    pause
    exit /b 1
)

python "%HERE%clipboard_keeper.py" --console
pause
