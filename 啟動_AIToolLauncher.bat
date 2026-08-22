@echo off
title AI Tool Launcher Setup

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

:: Check for winget
winget --version >nul 2>&1
set WINGET_AVAILABLE=%errorlevel%

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    if "%WINGET_AVAILABLE%"=="0" (
        echo [Auto-Install] Trying to install Python using Windows Package Manager...
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        echo ==========================================
        echo [SUCCESS] Python has been installed.
        echo Please CLOSE this black window and double-click the BAT file again to continue!
        echo ==========================================
    ) else (
        echo Please install Python manually and check "Add python.exe to PATH".
        echo Download: https://www.python.org/downloads/
    )
    pause
    exit /b
)

:: Check Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not found!
    if "%WINGET_AVAILABLE%"=="0" (
        echo [Auto-Install] Trying to install Git using Windows Package Manager...
        winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
        echo ==========================================
        echo [SUCCESS] Git has been installed.
        echo Please CLOSE this black window and double-click the BAT file again to continue!
        echo ==========================================
    ) else (
        echo Please install Git manually.
        echo Download: https://git-scm.com/downloads
    )
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
