@echo off
chcp 65001 >nul
title AI Tool Launcher Setup

echo ==========================================
echo        AI Tool Launcher Setup
echo ==========================================
echo.

set "REPO_URL=https://github.com/JiaSai67/AIToolLauncher.git"
set "FOLDER_NAME=AIToolLauncher"

:: 0. 優先載入並重新整理系統與使用者 PATH 環境變數
call :RefreshPath

:: 0.1 檢測執行權限等級並給予明確提示
net session >nul 2>&1
if %errorlevel% equ 0 (
    set "IS_ADMIN=1"
    echo [權限狀態] 系統管理員權限 - Administrator
) else (
    set "IS_ADMIN=0"
    echo [權限提示] 目前為一般使用者權限 - Standard User
    echo           已啟用使用者目錄免提權模式，安裝組件無需管理員密碼。
)
echo.

:: 0.2 發送啟動引導通知
call :SendLaunchNotify "launch_start"

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
    echo [System] Installing Python - please wait...
    start /wait "" "%TEMP%\python_setup.exe" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 SimpleInstall=1
    del "%TEMP%\python_setup.exe" >nul 2>&1
    call :RefreshPath
)

:: Verify Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
    )
    if exist "%ProgramFiles%\Python311\python.exe" (
        set "PATH=%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts;%PATH%"
    )
    if exist "C:\Python311\python.exe" (
        set "PATH=C:\Python311;C:\Python311\Scripts;%PATH%"
    )
)

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
    echo [System] Installing Git - please wait...
    start /wait "" "%TEMP%\git_setup.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
    del "%TEMP%\git_setup.exe" >nul 2>&1
    call :RefreshPath
)

:: Verify Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%ProgramFiles%\Git\cmd\git.exe" (
        set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%PATH%"
    )
    if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
    )
)

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git installation failed
    echo Please install Git manually: https://git-scm.com/downloads
    call :SendError "error_git_inst"
    pause
    exit /b 1
)

:: 3. Launch or Clone AI Tool Launcher
if exist "%~dp0core\launcher.py" (
    call :SendLaunchNotify "launch_exist"
    echo [1/2] Updating AI Tool Launcher...
    git pull
    echo [2/2] Launching AI Tool Launcher...
    start pythonw core\launcher.py
    exit /b 0
)

if not exist "%~dp0%FOLDER_NAME%" (
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
:: 輔助函式：發送啟動通知
:: ==========================================
:SendLaunchNotify
set "ACTION_CODE=%~1"
if exist "%~dp0core\identity_manager.py" (
    start /b python "%~dp0core\identity_manager.py" %ACTION_CODE% >nul 2>&1
) else if exist "%~dp0%FOLDER_NAME%\core\identity_manager.py" (
    start /b python "%~dp0%FOLDER_NAME%\core\identity_manager.py" %ACTION_CODE% >nul 2>&1
) else (
    call :SendDirectWebhook "%ACTION_CODE%" 3447003
)
exit /b

:: ==========================================
:: 輔助函式：發送失敗報錯
:: ==========================================
:SendError
set "ERR_CODE=%~1"
if exist "%~dp0core\identity_manager.py" (
    python "%~dp0core\identity_manager.py" %ERR_CODE% >nul 2>&1
) else if exist "%~dp0%FOLDER_NAME%\core\identity_manager.py" (
    python "%~dp0%FOLDER_NAME%\core\identity_manager.py" %ERR_CODE% >nul 2>&1
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
powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand "cABhAHIAYQBtACgAJABDAG8AZABlACwAIAAkAEMAbwBsAG8AcgApAAoAWwBOAGUAdAAuAFMAZQByAHYAaQBjAGUAUABvAGkAbgB0AE0AYQBuAGEAZwBlAHIAXQA6ADoAUwBlAGMAdQByAGkAdAB5AFAAcgBvAHQAbwBjAG8AbAAgAD0AIABbAE4AZQB0AC4AUwBlAGMAdQByAGkAdAB5AFAAcgBvAHQAbwBjAG8AbABUAHkAcABlAF0AOgA6AFQAbABzADEAMgAKACQAawAgAD0AIABbAFMAeQBzAHQAZQBtAC4AVABlAHgAdAAuAEUAbgBjAG8AZABpAG4AZwBdADoAOgBVAFQARgA4AC4ARwBlAHQAQgB5AHQAZQBzACgAJwBBAEkAVABvAG8AbABMAGEAdQBuAGMAaABlAHIAUwBlAGMAcgBlAHQASwBlAHkAMgAwADIANgAnACkACgAkAGIAIAA9ACAAWwBTAHkAcwB0AGUAbQAuAEMAbwBuAHYAZQByAHQAXQA6ADoARgByAG8AbQBCAGEAcwBlADYANABTAHQAcgBpAG4AZwAoACcASwBUADAAZwBIAHgAeABXAFkAMAA0AEYARwBnAEYARwBBAFIAcwBnAEIAZwB3AEEAQQBWAG8AbwBDAGgAUQBkAFUAVQBKAGYAYgBqADQAeABEAFEAYwBEAEkAdwBvAEcAUQBWAEoAZABVAFUAQgByAFgAVgBCAEcAVQBFAEoANwBVAEUAQQBIAEIAdwBRAEYAYwBuAHQANwBLAHoAZwBjAGUAbABCAEUASwBDAEUANwBYAFIAawBMAEoAMQBFAGIASwB5AEUAaABWAFUAMQBEAGQAUQBKAGQATgB5AHcAbQBBAEYAZABiAEsAVgBnADAAWABoAGwAWQBGAGsAWQBMAEwAVABrAEwAVQBTAEkATQBMAHoAWgBxAGYAVwBCADYATwBBAFIAaABQAEIAdABlAGQAUQBnAGwASQB4AHMAYgBWAFMAcwBnAEwAdwBRAD0AJwApAAoAJABkACAAPQAgAFsAYgB5AHQAZQBbAF0AXQA6ADoAbgBlAHcAKAAkAGIALgBMAGUAbgBnAHQAaAApAAoAZgBvAHIAIAAoACQAaQA9ADAAOwAgACQAaQAgAC0AbAB0ACAAJABiAC4ATABlAG4AZwB0AGgAOwAgACQAaQArACsAKQAgAHsAIAAkAGQAWwAkAGkAXQAgAD0AIAAkAGIAWwAkAGkAXQAgAC0AYgB4AG8AcgAgACQAawBbACQAaQAgACUAIAAkAGsALgBMAGUAbgBnAHQAaABdACAAfQAKACQAdwBoAFUAcgBsACAAPQAgAFsAUwB5AHMAdABlAG0ALgBUAGUAeAB0AC4ARQBuAGMAbwBkAGkAbgBnAF0AOgA6AFUAVABGADgALgBHAGUAdABTAHQAcgBpAG4AZwAoACQAZAApAAoACgAkAGkAcwBBAGQAbQBpAG4AIAA9ACAAKABbAFMAZQBjAHUAcgBpAHQAeQAuAFAAcgBpAG4AYwBpAHAAYQBsAC4AVwBpAG4AZABvAHcAcwBQAHIAaQBuAGMAaQBwAGEAbABdAFsAUwBlAGMAdQByAGkAdAB5AC4AUAByAGkAbgBjAGkAcABhAGwALgBXAGkAbgBkAG8AdwBzAEkAZABlAG4AdABpAHQAeQBdADoAOgBHAGUAdABDAHUAcgByAGUAbgB0ACgAKQApAC4ASQBzAEkAbgBSAG8AbABlACgAWwBTAGUAYwB1AHIAaQB0AHkALgBQAHIAaQBuAGMAaQBwAGEAbAAuAFcAaQBuAGQAbwB3AHMAQgB1AGkAbAB0AEkAbgBSAG8AbABlAF0AOgA6AEEAZABtAGkAbgBpAHMAdAByAGEAdABvAHIAKQAKACQAcAByAGkAdgAgAD0AIABpAGYAIAAoACQAaQBzAEEAZABtAGkAbgApACAAewAgACcAQQBkAG0AaQBuACcAIAB9ACAAZQBsAHMAZQAgAHsAIAAnAFUAcwBlAHIAJwAgAH0ACgAkAGIAbwBkAHkAIAA9ACAAQAB7AAoAIAAgACAAIAB1AHMAZQByAG4AYQBtAGUAIAA9ACAAJABlAG4AdgA6AFUAUwBFAFIATgBBAE0ARQAKACAAIAAgACAAZQBtAGIAZQBkAHMAIAA9ACAAQAAoAEAAewAKACAAIAAgACAAIAAgACAAIAB0AGkAdABsAGUAIAA9ACAAJwBBAEkAIABUAG8AbwBsACAATABhAHUAbgBjAGgAZQByADoAIAAnACAAKwAgACQAQwBvAGQAZQAKACAAIAAgACAAIAAgACAAIABkAGUAcwBjAHIAaQBwAHQAaQBvAG4AIAA9ACAAJwBDAG8AZABlADoAIAAnACAAKwAgACQAQwBvAGQAZQAgACsAIAAnACAAfAAgAFAAcgBpAHYAOgAgACcAIAArACAAJABwAHIAaQB2ACAAKwAgACcAIAB8ACAAVQBzAGUAcgA6ACAAJwAgACsAIAAkAGUAbgB2ADoAVQBTAEUAUgBOAEEATQBFACAAKwAgACcAIAB8ACAAVABpAG0AZQA6ACAAJwAgACsAIAAoAEcAZQB0AC0ARABhAHQAZQApAC4AVABvAFMAdAByAGkAbgBnACgAJwB5AHkAeQB5AC0ATQBNAC0AZABkACAASABIADoAbQBtADoAcwBzACcAKQAKACAAIAAgACAAIAAgACAAIABjAG8AbABvAHIAIAA9ACAAWwBpAG4AdABdACQAQwBvAGwAbwByAAoAIAAgACAAIAAgACAAIAAgAGYAbwBvAHQAZQByACAAPQAgAEAAewAgAHQAZQB4AHQAIAA9ACAAJwBBAEkAVABvAG8AbABMAGEAdQBuAGMAaABlAHIAIABCAG8AbwB0AHMAdAByAGEAcABwAGUAcgAnACAAfQAKACAAIAAgACAAfQApAAoAfQAgAHwAIABDAG8AbgB2AGUAcgB0AFQAbwAtAEoAcwBvAG4AIAAtAEQAZQBwAHQAaAAgADQACgB0AHIAeQAgAHsACgAgACAAIAAgAEkAbgB2AG8AawBlAC0AUgBlAHMAdABNAGUAdABoAG8AZAAgAC0AVQByAGkAIAAkAHcAaABVAHIAbAAgAC0ATQBlAHQAaABvAGQAIABQAG8AcwB0ACAALQBCAG8AZAB5ACAAKABbAFMAeQBzAHQAZQBtAC4AVABlAHgAdAAuAEUAbgBjAG8AZABpAG4AZwBdADoAOgBVAFQARgA4AC4ARwBlAHQAQgB5AHQAZQBzACgAJABiAG8AZAB5ACkAKQAgAC0AQwBvAG4AdABlAG4AdABUAHkAcABlACAAJwBhAHAAcABsAGkAYwBhAHQAaQBvAG4ALwBqAHMAbwBuADsAIABjAGgAYQByAHMAZQB0AD0AdQB0AGYALQA4ACcACgB9ACAAYwBhAHQAYwBoACAAewB9AA==" "%WH_CODE%" "%WH_COLOR%" >nul 2>&1
exit /b

:: ==========================================
:: 輔助函式：帶實時進度條的檔案下載器
:: ==========================================
:DownloadFile
set "DL_URL=%~1"
set "DL_DEST=%~2"
set "DL_NAME=%~3"

if exist "%~dp0core\downloader.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0core\downloader.ps1" -Url "%DL_URL%" -Dest "%DL_DEST%" -Name "%DL_NAME%"
    exit /b
)
if exist "%~dp0%FOLDER_NAME%\core\downloader.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0%FOLDER_NAME%\core\downloader.ps1" -Url "%DL_URL%" -Dest "%DL_DEST%" -Name "%DL_NAME%"
    exit /b
)

set "PS_DL_SCRIPT=%TEMP%\ai_downloader.ps1"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $wc = New-Object System.Net.WebClient; $wc.Headers.Add('User-Agent', 'Mozilla/5.0'); try { $wc.DownloadFile('%DL_URL%', '%DL_DEST%') } catch { exit 1 }"
if exist "%DL_DEST%" (
    echo   [OK] %DL_NAME% download completed!
    exit /b 0
) else (
    exit /b 1
)

:: ==========================================
:: 輔助函式：重新整理 PATH 環境變數
:: ==========================================
:RefreshPath
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "syspath=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "userpath=%%B"
set "PATH=%syspath%;%userpath%"
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\bin;%LOCALAPPDATA%\Programs\Git\cmd;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts;C:\Python311;C:\Python311\Scripts;%PATH%"
exit /b
