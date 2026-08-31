@echo off
chcp 65001 >nul
title AI Tool Launcher 1.0

cd /d "%~dp0"

echo ==========================================
echo           AI Tool Launcher 1.0
echo ==========================================
echo.

start "" pythonw core\launcher.py
exit /b 0
