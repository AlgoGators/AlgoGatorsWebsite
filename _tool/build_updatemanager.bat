@echo off
title Building UpdateManager.exe — AlgoGators
echo.
echo  AlgoGators Update Manager — Build Script
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo  [1/4] Installing dependencies...
pip install --quiet customtkinter tkinterdnd2 pyinstaller requests
if errorlevel 1 (
    echo  ERROR: pip install failed.
    pause
    exit /b 1
)

echo  [2/4] Copying source from repo root...
copy /Y ..\UpdateManager.pyw UpdateManager.pyw >nul

echo  [3/4] Building UpdateManager.exe...
pyinstaller UpdateManager.spec --noconfirm

if errorlevel 1 (
    echo  ERROR: PyInstaller failed.
    pause
    exit /b 1
)

echo  [4/4] Moving UpdateManager.exe to repo root...
if exist dist\UpdateManager.exe (
    copy /Y dist\UpdateManager.exe ..\UpdateManager.exe >nul
    echo.
    echo  Done!  UpdateManager.exe is ready at the repo root.
    echo  You can delete: build\  dist\  UpdateManager.pyw
) else (
    echo  ERROR: dist\UpdateManager.exe not found.
)

echo.
pause
