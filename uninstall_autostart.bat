@echo off
rem ClipboardKeeper - remove the startup shortcut
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%STARTUP%\ClipboardKeeper.bat" (
    del "%STARTUP%\ClipboardKeeper.bat"
    echo Autostart entry removed.
) else (
    echo No autostart entry found.
)
pause
