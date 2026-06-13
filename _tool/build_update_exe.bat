@echo off
title Building Update.exe — AlgoGators
echo.
echo  AlgoGators Update Tool — Build Script
echo  =======================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo  [1/3] Installing dependencies...
pip install --quiet customtkinter tkinterdnd2 pyinstaller requests
if errorlevel 1 (
    echo  ERROR: pip install failed.
    pause
    exit /b 1
)

echo  [2/3] Building Update.exe...
pyinstaller Update.spec --noconfirm

if errorlevel 1 (
    echo  ERROR: PyInstaller failed.
    pause
    exit /b 1
)

echo  [3/3] Moving Update.exe to repo root...
if exist dist\Update.exe (
    copy /Y dist\Update.exe ..\Update.exe >nul
    echo.
    echo  Done!  Update.exe is ready at the repo root.
    echo  You can delete: build\  dist\
) else (
    echo  ERROR: dist\Update.exe not found.
)

echo.
pause
