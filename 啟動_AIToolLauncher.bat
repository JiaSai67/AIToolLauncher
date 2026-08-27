@echo off
title AI Tool Launcher Setup

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

set "REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git"
set "FOLDER_NAME=AIToolLauncher"

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Python not found. Installing Python 3.11 automatically...
    echo [System] Downloading Python official installer from python.org...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'; $d=$env:TEMP + '\python_setup.exe'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $wc=New-Object System.Net.WebClient; $wc.Headers.Add('User-Agent','Mozilla/5.0'); try{$wc.OpenRead($u).Close(); $tot=[int64]$wc.ResponseHeaders['Content-Length']}catch{$tot=0}; $sw=[System.Diagnostics.Stopwatch]::StartNew(); $script:last=0; Register-ObjectEvent $wc DownloadProgressChanged -Action {$p=$EventArgs.ProgressPercentage; $rec=$EventArgs.BytesReceived; $t=$EventArgs.TotalBytesToReceive; if($t -le 0){$t=$tot}; $now=$sw.ElapsedMilliseconds; if($now - $script:last -ge 150 -or $p -eq 100){$mbR=($rec/1MB).ToString('0.0'); $mbT=if($t -gt 0){($t/1MB).ToString('0.0')}else{'???'}; $spd=if($now -gt 0){(($rec/1KB)/($now/1000)).ToString('0')}else{'0'}; $w=20; $fill=[int](($p/100)*$w); $bar='['+('='*$fill)+(' '*($w-$fill))+']'; Write-Host -NoNewline ('`r  -> Python 3.11: {0} {1,3}% ({2} MB / {3} MB) {4} KB/s   ' -f $bar, $p, $mbR, $mbT, $spd); $script:last=$now}} | Out-Null; $wc.DownloadFileAsync((New-Object System.Uri($u)), $d); while($wc.IsBusy){Start-Sleep -Milliseconds 50}; Write-Host ''"
    if not exist "%TEMP%\python_setup.exe" (
        echo [ERROR] Failed to download Python installer
        call :SendError "Python 安裝包下載失敗 (請檢查網路連線)"
        pause
        exit /b 1
    )
    echo [System] Installing Python quietly...
    start /wait "" "%TEMP%\python_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    del "%TEMP%\python_setup.exe" >nul 2>&1
    call :RefreshPath
)

:: Verify Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python installation failed
    echo Please install Python manually: https://www.python.org/downloads/
    call :SendError "Python 自動安裝失敗 (環境變數未生效或安裝受阻)"
    pause
    exit /b 1
)

:: 2. Check Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Git not found. Installing Git automatically...
    echo [System] Downloading Git installer from github.com...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe'; $d=$env:TEMP + '\git_setup.exe'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $wc=New-Object System.Net.WebClient; $wc.Headers.Add('User-Agent','Mozilla/5.0'); try{$wc.OpenRead($u).Close(); $tot=[int64]$wc.ResponseHeaders['Content-Length']}catch{$tot=0}; $sw=[System.Diagnostics.Stopwatch]::StartNew(); $script:last=0; Register-ObjectEvent $wc DownloadProgressChanged -Action {$p=$EventArgs.ProgressPercentage; $rec=$EventArgs.BytesReceived; $t=$EventArgs.TotalBytesToReceive; if($t -le 0){$t=$tot}; $now=$sw.ElapsedMilliseconds; if($now - $script:last -ge 150 -or $p -eq 100){$mbR=($rec/1MB).ToString('0.0'); $mbT=if($t -gt 0){($t/1MB).ToString('0.0')}else{'???'}; $spd=if($now -gt 0){(($rec/1KB)/($now/1000)).ToString('0')}else{'0'}; $w=20; $fill=[int](($p/100)*$w); $bar='['+('='*$fill)+(' '*($w-$fill))+']'; Write-Host -NoNewline ('`r  -> Git 64-bit:  {0} {1,3}% ({2} MB / {3} MB) {4} KB/s   ' -f $bar, $p, $mbR, $mbT, $spd); $script:last=$now}} | Out-Null; $wc.DownloadFileAsync((New-Object System.Uri($u)), $d); while($wc.IsBusy){Start-Sleep -Milliseconds 50}; Write-Host ''"
    if not exist "%TEMP%\git_setup.exe" (
        echo [ERROR] Failed to download Git installer
        call :SendError "Git 安裝包下載失敗 (請檢查網路連線)"
        pause
        exit /b 1
    )
    echo [System] Installing Git quietly...
    start /wait "" "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
    del "%TEMP%\git_setup.exe" >nul 2>&1
    call :RefreshPath
)

:: Verify Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git installation failed
    echo Please install Git manually: https://git-scm.com/downloads
    call :SendError "Git 自動安裝失敗 (環境變數未生效或安裝受阻)"
    pause
    exit /b 1
)

:: 3. Launch or Clone AI Tool Launcher
if exist "core\launcher.py" (
    call :SendLaunchNotify "更新並啟動已存在的 AI Tool Launcher"
    echo [1/2] Updating AI Tool Launcher...
    git pull
    echo [2/2] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit /b 0
)

if not exist "%FOLDER_NAME%" (
    call :SendLaunchNotify "首次安裝並下載 AI Tool Launcher (Git Clone)"
    echo [1/2] Downloading AI Tool Launcher from GitHub...
    git clone --progress %REPO_URL% %FOLDER_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Git clone failed
        call :SendError "Git Clone 下載主專案失敗 (請檢查連線或磁碟權限)"
        pause
        exit /b 1
    )
) else (
    call :SendLaunchNotify "更新並啟動 AI Tool Launcher (子目錄模式)"
    echo [1/2] Updating AI Tool Launcher...
    cd %FOLDER_NAME%
    git pull
    cd ..
)

echo [2/2] Launching AI Tool Launcher...
cd %FOLDER_NAME%
start pythonw core\launcher.py
exit /b 0

:: ==========================================
:: 輔助函式：發送啟動通知
:: ==========================================
:SendLaunchNotify
set "ACTION_DESC=%~1"
set "NOTIFY_BODY=[引導安裝器執行紀錄]^n動作: %ACTION_DESC%^n狀態: 環境檢查通過，正在載入核心模組^n時間: %DATE% %TIME%"
if exist "core\identity_manager.py" (
    start /b python core\identity_manager.py send "🚀 啟動安裝器：正在執行 AI Tool Launcher" "%NOTIFY_BODY%" 3447003 >nul 2>&1
) else if exist "%FOLDER_NAME%\core\identity_manager.py" (
    start /b python %FOLDER_NAME%\core\identity_manager.py send "🚀 啟動安裝器：正在執行 AI Tool Launcher" "%NOTIFY_BODY%" 3447003 >nul 2>&1
)
exit /b

:: ==========================================
:: 輔助函式：發送失敗報錯
:: ==========================================
:SendError
set "ERR_MSG=%~1"
set "ERR_BODY=[引導安裝器異常中斷報告]^n階段: 系統環境引導與安裝階段^n錯誤訊息: %ERR_MSG%^n時間: %DATE% %TIME%"
if exist "core\identity_manager.py" (
    python core\identity_manager.py send "💥 引導安裝器異常中斷" "%ERR_BODY%" 15158332 >nul 2>&1
) else if exist "%FOLDER_NAME%\core\identity_manager.py" (
    python %FOLDER_NAME%\core\identity_manager.py send "💥 引導安裝器異常中斷" "%ERR_BODY%" 15158332 >nul 2>&1
)
exit /b

:: ==========================================
:: 輔助函式：重新整理 PATH 環境變數
:: ==========================================
:RefreshPath
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;C:\Python311;C:\Python311\Scripts;%PATH%"
exit /b
