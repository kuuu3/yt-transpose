@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ====================================
echo YouTube Audio Transpose Tool
echo ====================================
echo.

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :check_python_done
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :check_python_done
)

echo [ERROR] Python not found. Please install Python 3.8 or higher
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:check_python_done
echo [OK] Python installed
%PYTHON_CMD% --version

echo.
echo Checking environment...
%PYTHON_CMD% setup_env.py
if not %errorlevel% equ 0 (
    echo.
    echo [ERROR] Environment setup failed. Please check error messages above.
    pause
    exit /b 1
)

echo.
echo Starting application...
%PYTHON_CMD% app.py

if not %errorlevel% equ 0 (
    echo.
    echo [ERROR] Application execution failed.
    pause
    exit /b 1
)

exit /b 0
