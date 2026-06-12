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
pip install --quiet customtkinter tkinterdnd2 pyinstaller
if errorlevel 1 (
    echo  ERROR: pip install failed.
    pause
    exit /b 1
)

echo  [2/3] Building Update.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name Update ^
    --add-data "update_tool.py;." ^
    --hidden-import customtkinter ^
    --hidden-import tkinterdnd2 ^
    update_tool.py

if errorlevel 1 (
    echo  ERROR: PyInstaller failed.
    pause
    exit /b 1
)

echo  [3/3] Moving Update.exe here...
if exist dist\Update.exe (
    copy /Y dist\Update.exe Update.exe >nul
    echo.
    echo  Done!  Update.exe is ready in this folder.
    echo  You can delete: build\  dist\  Update.spec
) else (
    echo  ERROR: dist\Update.exe not found.
)

echo.
pause
