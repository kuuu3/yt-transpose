Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "python setup_env.py >nul 2>&1", 0, True
WshShell.Run "python app.py", 0
Set WshShell = Nothing


