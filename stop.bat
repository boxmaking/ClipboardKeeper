@echo off
rem ClipboardKeeper - stop the background process
setlocal
set "HERE=%~dp0"
set "PIDFILE=%HERE%run.pid"

if exist "%PIDFILE%" (
    set /p KPID=<"%PIDFILE%"
    taskkill /PID %KPID% /F >nul 2>&1
    del "%PIDFILE%" >nul 2>&1
    echo ClipboardKeeper stopped.
    exit /b 0
)

echo No run.pid found, trying to find the process by command line...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*clipboard_keeper.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo Done.
exit /b 0
