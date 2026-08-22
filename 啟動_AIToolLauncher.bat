@echo off
title AI Tool Launcher Setup

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python and check "Add python.exe to PATH" during installation.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b
)

:: Check Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed!
    echo Please install Git.
    echo Download: https://git-scm.com/downloads
    pause
    exit /b
)

set REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git
set FOLDER_NAME=AIToolLauncher

if not exist "%FOLDER_NAME%" (
    echo [1/3] Downloading AI Tool Launcher from GitHub...
    git clone %REPO_URL% %FOLDER_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Download failed. Please check your internet connection.
        pause
        exit /b
    )
) else (
    echo [1/3] Checking for core updates...
    cd %FOLDER_NAME%
    git pull
    cd ..
)

echo [2/3] Installing dependencies...
cd %FOLDER_NAME%
python -m pip install -r requirements.txt >nul 2>&1

echo [3/3] Starting Launcher...
start pythonw core\launcher.py

exit
