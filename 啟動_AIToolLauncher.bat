@echo off
title AI Tool Launcher Setup
setlocal enabledelayedexpansion

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Python not found. Installing Python 3.11 automatically...
    echo [System] Downloading Python official installer (with progress)...
    
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $ProgressPreference = 'Continue'; $wc = New-Object System.Net.WebClient; $wc.DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', [System.IO.Path]::GetTempPath() + 'python_setup.exe'); exit 0 } catch { Write-Host '[ERROR]' $_.Exception.Message; exit 1 }"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to download Python installer! Please check your internet connection.
        pause
        exit /b 1
    )
    
    if exist "%TEMP%\python_setup.exe" (
        echo [System] Installing Python quietly...
        start /wait "" "%TEMP%\python_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
        del "%TEMP%\python_setup.exe" >nul 2>&1
    )
    call :RefreshPath
)

:: Verify Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python installation failed or was interrupted.
    echo Please install Python manually: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 2. Check Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Git not found. Installing Git automatically...
    echo [System] Downloading Git installer (60MB, please wait)...
    
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Start-BitsTransfer -Source 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe' -Destination ([System.IO.Path]::GetTempPath() + 'git_setup.exe') -DisplayName 'Downloading Git 64-bit'; exit 0 } catch { try { $wc = New-Object System.Net.WebClient; $wc.DownloadFile('https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe', [System.IO.Path]::GetTempPath() + 'git_setup.exe'); exit 0 } catch { Write-Host '[ERROR]' $_.Exception.Message; exit 1 } }"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to download Git installer from GitHub!
        echo Please check your internet connection or firewall.
        pause
        exit /b 1
    )
    
    if exist "%TEMP%\git_setup.exe" (
        echo [System] Installing Git in background (Please wait 10-20 seconds)...
        start /wait "" "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
        del "%TEMP%\git_setup.exe" >nul 2>&1
    )
    call :RefreshPath
)

:: Verify Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git installation failed or was interrupted.
    echo Please install Git manually: https://git-scm.com/downloads
    pause
    exit /b 1
)

:: 3. Launch or Clone AI Tool Launcher
set REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git
set FOLDER_NAME=AIToolLauncher

if exist "core\launcher.py" (
    echo [1/2] Updating AI Tool Launcher...
    git pull
    if !errorlevel! neq 0 (
        echo [WARN] Update skipped. Launching current version...
    )
    echo [2/2] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit /b 0
)

if not exist "%FOLDER_NAME%" (
    echo [1/2] Downloading AI Tool Launcher from GitHub (progress below)...
    git clone --progress %REPO_URL% %FOLDER_NAME%
    if !errorlevel! neq 0 (
        echo [ERROR] Git clone failed. Please check internet connection.
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

:RefreshPath
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;C:\Python311;C:\Python311\Scripts;%PATH%"
exit /b
