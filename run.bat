@echo off
rem 使用 VBScript 啟動以避免顯示命令提示字元視窗
rem 如果仍看到命令提示字元，請直接雙擊 launcher.vbs
start "" /min wscript.exe //E:VBScript //B //Nologo "%~dp0launcher.vbs"
timeout /t 1 /nobreak >nul
exit
