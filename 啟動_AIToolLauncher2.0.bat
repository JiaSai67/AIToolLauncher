@echo off
chcp 65001 >nul
title AI Tool Launcher 2.0 [收納盒模式]

cd /d "%~dp0"

echo ==========================================
echo       AI Tool Launcher 2.0 (收納盒模式)
echo ==========================================
echo.

start "" pythonw core\launcher_v2.py
exit /b 0
