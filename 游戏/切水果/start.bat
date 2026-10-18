@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title Fruit Flash - Gesture Server
cd /d "%~dp0"

set "FRUIT_PYTHON=python"
if exist "%~dp0.venv\Scripts\python.exe" goto environment_ready
"%FRUIT_PYTHON%" "%~dp0setup_env.py"
if errorlevel 1 goto install_error
:environment_ready
set "FRUIT_PYTHON=%~dp0.venv\Scripts\python.exe"

echo ============================================
echo   Fruit Flash - Gesture Recognition
echo ============================================
echo.

"%FRUIT_PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto python_error

"%FRUIT_PYTHON%" -c "import cv2, numpy, aiohttp; from mediapipe.tasks.python import vision" >nul 2>nul
if not errorlevel 1 goto run_server

echo [Setup] Installing missing Python dependencies...
"%FRUIT_PYTHON%" "%~dp0setup_env.py"
if errorlevel 1 goto install_error

:run_server
echo [Start] Starting the gesture server...
echo [Info] A hand model will be downloaded if no local model is available.
echo.
"%FRUIT_PYTHON%" "%~dp0backend\main.py" %*
set "FRUIT_EXIT_CODE=%ERRORLEVEL%"
if not "%FRUIT_EXIT_CODE%"=="0" echo [Error] The server exited with code %FRUIT_EXIT_CODE%.
goto finish

:python_error
echo [Error] Python 3.10 or newer is required. Python 3.12 is recommended.
echo [Info] Download Python from https://www.python.org/downloads/
set "FRUIT_EXIT_CODE=1"
goto finish

:install_error
echo [Error] Dependency installation failed. See the messages above.
set "FRUIT_EXIT_CODE=1"

:finish
echo.
pause
exit /b %FRUIT_EXIT_CODE%
