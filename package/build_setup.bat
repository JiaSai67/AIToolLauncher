@echo off
set CSC=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
cd /d "%~dp0"

echo [1/3] Compiling AIToolLauncher_Setup.cs ...
%CSC% /target:winexe /optimize+ /platform:x64 /win32icon:"..\resources\icon.ico" /out:"..\AIToolLauncher_Setup.exe" /r:System.dll /r:System.Core.dll /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll AIToolLauncher_Setup.cs

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

echo [2/3] Copying binaries ...
copy /y "..\AIToolLauncher_Setup.exe" "AIToolLauncher_Setup.exe" >nul

echo [3/3] Done successfully!
