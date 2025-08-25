@echo off
title Database Sync Tool
echo Starting Database Sync...
echo.

REM Check if sync.exe exists
if exist sync.exe (
    sync.exe
) else (
    echo ERROR: sync.exe not found!
    echo Please make sure sync.exe is in the same folder as this batch file.
    pause
    exit /b 1
)

echo.
echo Sync process completed.
pause