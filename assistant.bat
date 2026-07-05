@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv312\Scripts\pythonw.exe"

if not exist "%PYTHON%" set "PYTHON=%ROOT%.venv312\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Python 3.12 virtual environment not found at "%ROOT%.venv312".
    pause
    exit /b 1
)

start "" /D "%ROOT%core" "%PYTHON%" assistant.py

endlocal