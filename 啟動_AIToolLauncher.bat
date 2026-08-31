@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AIToolLauncher 2.0
if exist "AIToolLauncher.exe" (
    start "" "AIToolLauncher.exe"
) else (
    start "" pythonw core\launcher_v2.py
)
exit /b 0
