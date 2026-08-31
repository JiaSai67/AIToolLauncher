@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 檢查是否有 Python
python --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    set "PYTHONW_CMD=pythonw"
    goto check_done
)

echo ========================================================
echo 系統未偵測到 Python，準備為您自動下載並安裝 Python 3.11
echo ========================================================

if not exist "python_installer.exe" (
    echo 正在下載 Python 3.11 安裝檔 (約 25MB)，請稍候...
    curl -# -L -o python_installer.exe "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
)

echo 正在背景靜默安裝 Python (可能需要 1~3 分鐘)，請稍候...
start /wait "" python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
echo 安裝完成！

:: 設定剛安裝的 Python 路徑 (避免 CMD 沒有即時更新 PATH)
set "PYTHON_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
set "PYTHONW_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\pythonw.exe"

if not exist "%PYTHON_CMD%" (
    echo [錯誤] 找不到安裝好的 Python，請檢查防毒軟體或手動安裝。
    pause
    exit /b 1
)

:check_done
if exist requirements.txt (
    "%PYTHON_CMD%" -m pip install -r requirements.txt >nul 2>&1
)

start "" "%PYTHONW_CMD%" launcher.py
