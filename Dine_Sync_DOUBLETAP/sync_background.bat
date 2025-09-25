@echo off
REM Run sync in background without console window
if exist sync.exe (
    start /min sync.exe
) else (
    echo ERROR: sync.exe not found!
    pause
)
