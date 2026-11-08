@echo off
rem ClipboardKeeper - register a startup shortcut in the user Startup folder
setlocal
set "HERE=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

where pythonw >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pythonw.exe not found in PATH.
    pause
    exit /b 1
)

> "%STARTUP%\ClipboardKeeper.bat" echo @echo off
>> "%STARTUP%\ClipboardKeeper.bat" echo start "" pythonw "%HERE%clipboard_keeper.py"

echo Autostart entry created:
echo   %STARTUP%\ClipboardKeeper.bat
pause
