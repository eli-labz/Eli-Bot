@echo off
setlocal

set "ROOT=%~dp0"
set "CORE_DIR=%ROOT%core"
set "APP_ENTRY=%CORE_DIR%\assistant.py"
set "ENV_FILE=%CORE_DIR%\.env"
set "MODEL_DIR=%CORE_DIR%\model\MiniCPM5-1B"
set "ROOT_MODEL_DIR=%ROOT%model\MiniCPM5-1B"
set "ALLOW_ROOT_MODEL_HINT=1"
set "ALLOW_ROOT_MODEL_AUTOLINK=1"

set "PYTHON=%ROOT%.venv312\Scripts\pythonw.exe"

if "%ELI_BOT_CONSOLE%"=="1" set "PYTHON=%ROOT%.venv312\Scripts\python.exe"

if not exist "%PYTHON%" set "PYTHON=%ROOT%.venv312\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Python 3.12 virtual environment not found at "%ROOT%.venv312".
    pause
    exit /b 1
)

if exist "%ENV_FILE%" (
    for /f "usebackq eol=# tokens=1* delims==" %%A in ("%ENV_FILE%") do (
        if not "%%A"=="" set "%%A=%%~B"
    )
)

if not exist "%APP_ENTRY%" (
    echo Entry script not found: "%APP_ENTRY%"
    pause
    exit /b 1
)

if not exist "%MODEL_DIR%" (
    if "%ALLOW_ROOT_MODEL_AUTOLINK%"=="1" if exist "%ROOT_MODEL_DIR%" (
        if not exist "%CORE_DIR%\model" mkdir "%CORE_DIR%\model"
        mklink /J "%MODEL_DIR%" "%ROOT_MODEL_DIR%" >nul 2>&1
    )
)

if not exist "%MODEL_DIR%" (
    echo MiniCPM model directory not found: "%MODEL_DIR%"
    if "%ALLOW_ROOT_MODEL_HINT%"=="1" if exist "%ROOT_MODEL_DIR%" (
        echo Found a root-level model copy at: "%ROOT_MODEL_DIR%"
        echo Automatic linking failed. You can run this once:
        echo   mklink /J "%MODEL_DIR%" "%ROOT_MODEL_DIR%"
    ) else (
        echo Expected local model files under core\model\MiniCPM5-1B before launching Eli Bot.
    )
    exit /b 1
)

start "" /D "%CORE_DIR%" "%PYTHON%" "%APP_ENTRY%"

endlocal
exit /b 0