@echo off
chcp 65001 >nul
title AI Tool Launcher 1.0

cd /d "%~dp0"
start "" pythonw core\launcher.py
exit /b 0
