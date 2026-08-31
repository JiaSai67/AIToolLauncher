# AI Tool Launcher

This is a central launcher for various AI and automation projects.

## Agent Instructions: How to Register a Project

If you are an AI agent setting up a new project, you MUST generate a `linkme.bat` file in the root directory of the new project. This file allows the user to easily register the project into this launcher by double-clicking it.

Below is the standard template for `linkme.bat`. You MUST fill in the `<PROJECT_NAME>`, `<PROJECT_DESC>`, and `<EXEC_FILENAME>` fields appropriately. The `<EXEC_FILENAME>` should be the main script or batch file that launches the project (e.g., `start.bat` or `main.py`).

```bat
@echo off
chcp 65001 >nul
set CWD=%~dp0
if "%CWD:~-1%"=="\" set CWD=%CWD:~0,-1%

:: Define Project Name and Description here
set PROJECT_NAME=<PROJECT_NAME>
set PROJECT_DESC=<PROJECT_DESC>
set EXEC_FILE=%CWD%\<EXEC_FILENAME>

echo Registering %PROJECT_NAME% to AI Tool Launcher...
python "g:\python\toolLauncher\register_api.py" --name "%PROJECT_NAME%" --desc "%PROJECT_DESC%" --exec "%EXEC_FILE%" --cwd "%CWD%"

echo.
echo Registration complete! You can now close this window.
pause
```

### Important constraints for project `.bat` launch scripts:
When you create a `.bat` launch script for a project (e.g., `start.bat`), you MUST follow these 4 rules:
1. **NO UI Interaction / Blocking**: The `.bat` script MUST NOT contain `pause` or ask for user input. It must run completely unattended.
2. **Handle Hidden Output**: Since the Launcher executes the `.bat` file with a hidden window (`CREATE_NO_WINDOW`), any output to `stdout` or `stderr` will NOT be visible to the user. If the project needs to output logs, it MUST redirect them to a file (e.g., `python main.py > startup.log 2>&1`).
3. **No Directory Switching Needed**: The Launcher automatically sets the working directory when starting the subprocess, so the `.bat` script does NOT need to `cd` into the directory.
4. **Blocking Execution**: The `.bat` script must block until the main application closes (i.e. do not use `start` unless it's `start /wait`). If it exits immediately, the Launcher will falsely report that the program has ended.

### Example standard `start.bat` template:
```bat
@echo off
chcp 65001 >nul
:: AI Tool Launcher Compatible Script

:: Activate virtual environment if applicable
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat

:: Execute main logic and redirect logs
python main.py > startup.log 2>&1
```
