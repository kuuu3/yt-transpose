@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================
echo YouTube 音檔轉調工具
echo ====================================
echo.

REM 檢查並設置環境
python setup_env.py
if errorlevel 1 (
    echo.
    echo 環境設置失敗，請檢查錯誤訊息
    pause
    exit /b 1
)

echo.
echo 啟動應用程式...
python app.py

if errorlevel 1 (
    echo.
    echo 應用程式執行錯誤
    pause
    exit /b 1
)

exit

