@echo off
chcp 65001 >nul
title AI Tool Launcher

cd /d "%~dp02.0"
if exist "core\launcher_v2.py" (
    start "" pythonw core\launcher_v2.py
    exit /b 0
)

cd /d "%~dp01.0"
if exist "core\launcher.py" (
    start "" pythonw core\launcher.py
    exit /b 0
)
