@echo off
chcp 65001 >nul
title AI Tool Launcher 一鍵修復與極速更新
color 0B

echo ========================================================
echo       AI Tool Launcher 2.0 一鍵修復與極速更新工具
echo ========================================================
echo.

:: 1. 關閉任何可能卡死或殘留的舊進程，釋放 Windows 檔案鎖
echo [1/4] 正在檢查並終止殘留進程...
taskkill /F /FI "WINDOWTITLE eq AI Tool Launcher*" >nul 2>&1
taskkill /F /IM AIToolLauncher.exe >nul 2>&1
timeout /t 1 /nobreak >nul

cd /d "%~dp0"

:: 2. 檢查 Git 環境與版本庫綁定 (支援非 Git 目錄自動初始化與 ZIP 備援)
echo [2/4] 正在檢查並同步 GitHub 主倉庫 (main)...
if not exist ".git" (
    where git >nul 2>&1
    if not errorlevel 1 (
        echo [提示] 偵測到本機目錄尚未關聯 Git 版本庫，正在自動初始化並綁定 GitHub 主倉庫...
        git init --quiet
        git remote add origin https://github.com/JiaSai67/AIToolLauncher.git >nul 2>&1
        git fetch origin main --depth=1 --quiet
        git reset --hard origin/main --quiet
        git branch -M main >nul 2>&1
        git branch --set-upstream-to=origin/main main >nul 2>&1
    ) else (
        echo [提示] 本機未安裝 Git，正在使用 GitHub 高速 ZIP 下載更新通道...
        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $z = Join-Path $env:TEMP 'aitoollauncher_upd.zip'; Invoke-WebRequest -Uri 'https://github.com/JiaSai67/AIToolLauncher/archive/refs/heads/main.zip' -OutFile $z; $ex = Join-Path $env:TEMP 'aitoollauncher_upd_dir'; if (Test-Path $ex) { Remove-Item $ex -Recurse -Force }; Expand-Archive -Path $z -DestinationPath $ex -Force; Copy-Item -Path \"$ex\AIToolLauncher-main\*\" -Destination '%CD%' -Recurse -Force; Remove-Item $z -Force; Remove-Item $ex -Recurse -Force"
    )
) else (
    git fetch origin main --quiet
    if errorlevel 1 (
        echo ⚠️ 連線 GitHub 逾時，嘗試以目前本地版本進行重設...
    )
    git reset --hard origin/main
    git clean -fd -e runtime -e CloudTools -e .env -e *.log
)

:: 3. 清理歷史殘留與快取檔案
echo [3/4] 正在清理無效殘留 (1.0、舊快取)...
if exist "1.0" rd /s /q "1.0" >nul 2>&1
if exist "core\launcher.py" del /f /q "core\launcher.py" >nul 2>&1

:: 4. 啟動最新版本
echo [4/4] 正在啟動最新版本 AI Tool Launcher...
echo.
echo ========================================================
echo   🎉 修復與更新完成！已為您成功更新至最新發布版本。
echo ========================================================
timeout /t 1 /nobreak >nul

if exist "AIToolLauncher.exe" (
    start "" "AIToolLauncher.exe"
) else if exist "啟動_AIToolLauncher.bat" (
    start "" "啟動_AIToolLauncher.bat"
) else (
    start "" pythonw core\launcher_v2.py
)

exit /b 0
