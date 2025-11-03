@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================
echo YouTube 音檔轉調工具
echo ====================================
echo.

REM 檢查 Python 是否安裝（嘗試 python 和 py 兩種命令）
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [錯誤] 找不到 Python，請先安裝 Python 3.8 或更高版本
        echo 下載連結：https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo [OK] Python 已安裝
%PYTHON_CMD% --version

REM 檢查並設置環境
echo.
echo 正在檢查環境...
%PYTHON_CMD% setup_env.py
if errorlevel 1 (
    echo.
    echo [錯誤] 環境設置失敗，請檢查上述錯誤訊息
    pause
    exit /b 1
)

echo.
echo 正在啟動應用程式...
%PYTHON_CMD% app.py

if errorlevel 1 (
    echo.
    echo [錯誤] 應用程式執行錯誤
    pause
    exit /b 1
)

exit

