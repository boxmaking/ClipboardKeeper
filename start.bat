@echo off
rem ClipboardKeeper - start in background (no console window)
setlocal
set "HERE=%~dp0"

if exist "%HERE%run.pid" (
    echo ClipboardKeeper seems to be running already.
    echo Run stop.bat first if you want to restart it.
    pause
    exit /b 1
)

where pythonw >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pythonw.exe not found in PATH.
    echo Install Python 3.8+ and tick "Add Python to PATH".
    pause
    exit /b 1
)

start "" pythonw "%HERE%clipboard_keeper.py"
echo ClipboardKeeper started in background.
exit /b 0
