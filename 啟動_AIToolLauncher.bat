@echo off
title AI Tool Launcher Setup
setlocal enabledelayedexpansion

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo Please install Python 3.11 from: https://www.python.org/downloads/
    echo Remember to check 'Add python.exe to PATH' during installation.
    pause
    exit /b 1
)

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed.
    echo Please install Git from: https://git-scm.com/downloads
    pause
    exit /b 1
)

set REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git
set FOLDER_NAME=AIToolLauncher

if exist "core\launcher.py" (
    echo [1/2] Updating AI Tool Launcher...
    git pull
    echo [2/2] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit /b 0
)

if not exist "%FOLDER_NAME%" (
    echo [1/2] Downloading AI Tool Launcher from GitHub...
    git clone %REPO_URL% %FOLDER_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Git clone failed. Please check your internet connection.
        pause
        exit /b 1
    )
) else (
    echo [1/2] Updating AI Tool Launcher...
    cd %FOLDER_NAME%
    git pull
    cd ..
)

echo [2/2] Launching AI Tool Launcher...
cd %FOLDER_NAME%
start pythonw core\launcher.py
exit /b 0
