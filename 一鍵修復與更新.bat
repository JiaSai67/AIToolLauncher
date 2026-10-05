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

:: 2. 拉取主倉庫最新發布內容
echo [2/4] 正在從 GitHub 拉取最新主分支 (main)...
git fetch origin main --quiet
if errorlevel 1 (
    echo ⚠️ 連線 GitHub 逾時，嘗試以目前本地版本進行重設...
)

:: 3. 強制重設與清理歷史殘留檔案
echo [3/4] 正在重設工作目錄並清理無效殘留 (1.0、舊快取)...
git reset --hard origin/main
git clean -fd -e runtime -e CloudTools -e .env -e *.log

:: 清理歷史殘留 1.0 資料夾
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
