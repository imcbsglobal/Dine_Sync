@echo off
title Database Sync Tool - Console
color 0A
echo.
echo ===============================================
echo           DATABASE SYNC TOOL
echo ===============================================
echo.

REM Check if sync.exe exists
if exist sync.exe (
    echo Starting sync process...
    echo.
    sync.exe
) else (
    echo ERROR: sync.exe not found!
    echo Please make sure sync.exe is in the same folder as this batch file.
    echo.
    pause
    exit /b 1
)

echo.
echo Sync process completed.
echo Check sync.log for detailed information.
pause
