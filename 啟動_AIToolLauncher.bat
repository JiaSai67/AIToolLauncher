@echo off
title AI Tool Launcher Setup
setlocal enabledelayedexpansion

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

:check_python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [Auto-Install] Installing Python... Please wait.
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        python --version >nul 2>&1
        if !errorlevel! equ 0 goto :check_git
    )
    echo =======================================================
    echo [錯誤] 找不到 Python，且系統無 winget 自動安裝支援。
    echo 請手動下載並安裝 Python (勾選 Add Python to PATH)：
    echo https://www.python.org/downloads/
    echo =======================================================
    pause
    exit /b
)

:check_git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not found!
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [Auto-Install] Installing Git... Please wait.
        winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        git --version >nul 2>&1
        if !errorlevel! equ 0 goto :start_setup
    )
    echo =======================================================
    echo [錯誤] 找不到 Git，且系統無 winget 自動安裝支援。
    echo 請手動下載並安裝 Git：
    echo https://git-scm.com/downloads
    echo =======================================================
    pause
    exit /b
)

:start_setup

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

:RefreshPath
echo [System] Refreshing Environment Variables...
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
exit /b
