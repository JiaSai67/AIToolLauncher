@echo off
title AI Tool Launcher Setup
setlocal enabledelayedexpansion
chcp 65001 >nul

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

:check_python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo [Auto-Install] Attempting Python auto-install...
    
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        python --version >nul 2>&1
        if !errorlevel! equ 0 goto :check_git
    )
    
    echo [Auto-Install] Downloading Python 3.11 from python.org...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '$env:TEMP\python_setup.exe'"
    if exist "%TEMP%\python_setup.exe" (
        echo [Auto-Install] Installing Python in background...
        "%TEMP%\python_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
        del "%TEMP%\python_setup.exe" >nul 2>&1
        call :RefreshPath
        python --version >nul 2>&1
        if !errorlevel! equ 0 goto :check_git
    )
    
    echo =======================================================
    echo [ERROR] Python auto-install failed.
    echo Please install Python manually (Check 'Add Python to PATH'):
    echo https://www.python.org/downloads/
    echo =======================================================
    pause
    exit /b
)

:check_git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not found.
    echo [Auto-Install] Attempting Git auto-install...
    
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        git --version >nul 2>&1
        if !errorlevel! equ 0 goto :start_setup
    )
    
    echo [Auto-Install] Downloading Git standalone installer...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe' -OutFile '$env:TEMP\git_setup.exe'"
    if exist "%TEMP%\git_setup.exe" (
        echo [Auto-Install] Installing Git in background (Please wait)...
        "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
        del "%TEMP%\git_setup.exe" >nul 2>&1
        call :RefreshPath
        git --version >nul 2>&1
        if !errorlevel! equ 0 goto :start_setup
    )

    echo =======================================================
    echo [ERROR] Git auto-install failed.
    echo Please install Git manually:
    echo https://git-scm.com/downloads
    echo =======================================================
    pause
    exit /b
)

:start_setup
set "REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git"
set "FOLDER_NAME=AIToolLauncher"

if exist "core\launcher.py" (
    echo [1/3] Checking core updates...
    git pull
    echo [2/3] Checking dependencies...
    python -m pip install -r requirements.txt >nul 2>&1
    echo [3/3] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit
)

if not exist "%FOLDER_NAME%" (
    echo [1/3] Downloading AI Tool Launcher from GitHub...
    git clone %REPO_URL% %FOLDER_NAME%
    if !errorlevel! neq 0 (
        echo [ERROR] Download failed. Please check your network.
        pause
        exit /b
    )
) else (
    echo [1/3] Checking updates...
    cd %FOLDER_NAME%
    git pull
    cd ..
)

echo [2/3] Checking dependencies...
cd %FOLDER_NAME%
python -m pip install -r requirements.txt >nul 2>&1

echo [3/3] Launching AI Tool Launcher...
start pythonw core\launcher.py
exit

:RefreshPath
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;C:\Python311;C:\Python311\Scripts;%PATH%"
exit /b
