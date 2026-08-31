@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AIToolLauncher 2.0
start "" pythonw core\launcher_v2.py
exit /b 0
