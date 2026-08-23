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
    echo [ERROR] 系統找不到 Python！
    echo [Auto-Install] 正在嘗試自動安裝 Python 3.11...
    
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        python --version >nul 2>&1
        if !errorlevel! equ 0 goto :check_git
    )
    
    echo [Auto-Install] 正在使用 PowerShell 下載 Python 官方安裝檔...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    if exist "%TEMP%\python_installer.exe" (
        echo [Auto-Install] 正在背景靜默安裝 Python...
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
        del "%TEMP%\python_installer.exe" >nul 2>&1
        call :RefreshPath
        python --version >nul 2>&1
        if !errorlevel! equ 0 goto :check_git
    )
    
    echo =======================================================
    echo [錯誤] 自動安裝 Python 失敗。
    echo 請手動下載安裝 (安裝時請務必勾選 Add Python to PATH)：
    echo https://www.python.org/downloads/
    echo =======================================================
    pause
    exit /b
)

:check_git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 系統找不到 Git！
    echo [Auto-Install] 正在嘗試自動安裝 Git...
    
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
        call :RefreshPath
        git --version >nul 2>&1
        if !errorlevel! equ 0 goto :start_setup
    )
    
    echo [Auto-Install] 正在從 GitHub 下載 Git 獨立安裝檔...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'"
    if exist "%TEMP%\git_installer.exe" (
        echo [Auto-Install] 正在背景靜默安裝 Git (請稍候)...
        "%TEMP%\git_installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
        del "%TEMP%\git_installer.exe" >nul 2>&1
        call :RefreshPath
        git --version >nul 2>&1
        if !errorlevel! equ 0 goto :start_setup
    )

    echo =======================================================
    echo [錯誤] 自動安裝 Git 失敗。
    echo 請手動下載並安裝 Git (按下一步到底即可)：
    echo https://git-scm.com/downloads
    echo =======================================================
    pause
    exit /b
)

:start_setup
set REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git
set FOLDER_NAME=AIToolLauncher

:: 判斷目前腳本是否已經在 AIToolLauncher 資料夾內部
if exist "core\launcher.py" (
    echo [1/3] 正在檢查大廳最新更新...
    git pull
    echo [2/3] 正在檢查依賴套件...
    python -m pip install -r requirements.txt >nul 2>&1
    echo [3/3] 正在啟動大廳...
    start pythonw core\launcher.py
    exit
)

:: 如果是獨立的啟動腳本 (放置在桌面等外部位置)
if not exist "%FOLDER_NAME%" (
    echo [1/3] 正在從 GitHub 下載 AI Tool Launcher 大廳...
    git clone %REPO_URL% %FOLDER_NAME%
    if !errorlevel! neq 0 (
        echo [ERROR] 下載失敗，請檢查網路連線。
        pause
        exit /b
    )
) else (
    echo [1/3] 正在檢查大廳更新...
    cd %FOLDER_NAME%
    git pull
    cd ..
)

echo [2/3] 正在安裝或檢查依賴套件...
cd %FOLDER_NAME%
python -m pip install -r requirements.txt >nul 2>&1

echo [3/3] 正在啟動大廳...
start pythonw core\launcher.py
exit

:RefreshPath
echo [System] 正在刷新環境變數 PATH...
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
exit /b
