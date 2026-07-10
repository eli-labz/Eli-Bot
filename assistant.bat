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

set "MODE=%~1"

if /I "%MODE%"=="/h" goto :usage
if /I "%MODE%"=="-h" goto :usage
if /I "%MODE%"=="/help" goto :usage
if /I "%MODE%"=="help" goto :usage
if /I "%MODE%"=="/?" goto :usage

if not "%MODE%"=="" (
    if /I "%MODE%"=="conversation" goto :mode_conversation
    if /I "%MODE%"=="automation" goto :mode_automation
    echo Unknown mode: "%MODE%"
    goto :usage_error
)
goto :mode_done

:mode_conversation
if not defined ELI_ASSISTANT_PROFILE set "ELI_ASSISTANT_PROFILE=conversation"
if not defined ELI_EDGE_ACTIONS_ENABLED set "ELI_EDGE_ACTIONS_ENABLED=false"
if not defined ELI_WORD_ACTIONS_ENABLED set "ELI_WORD_ACTIONS_ENABLED=true"
if not defined ENABLE_AUTORESEARCH_WORD set "ENABLE_AUTORESEARCH_WORD=false"
if not defined ELI_CONVERSATION_DIR set "ELI_CONVERSATION_DIR=%ROOT%data\conversation"
goto :mode_done

:mode_automation
if not defined ELI_ASSISTANT_PROFILE set "ELI_ASSISTANT_PROFILE=automation"
if not defined ELI_EDGE_ACTIONS_ENABLED set "ELI_EDGE_ACTIONS_ENABLED=true"
if not defined ELI_WORD_ACTIONS_ENABLED set "ELI_WORD_ACTIONS_ENABLED=true"
if not defined ENABLE_AUTORESEARCH_WORD set "ENABLE_AUTORESEARCH_WORD=false"
if not defined ELI_CONVERSATION_DIR set "ELI_CONVERSATION_DIR=%ROOT%data\conversation"
goto :mode_done

:mode_done

rem Match assistant.py runtime defaults unless the user explicitly sets environment variables.
set "PYTHONPATH=%CORE_DIR%;%ROOT%;%PYTHONPATH%"

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

:usage
echo Usage: assistant.bat [conversation^|automation]
echo.
echo Modes are optional and apply mode-specific defaults only when not already defined.
echo Existing environment variables are respected.
echo.
echo Examples:
echo   assistant.bat conversation
echo   assistant.bat automation
exit /b 0

:usage_error
echo.
echo Usage: assistant.bat [conversation^|automation]
exit /b 1