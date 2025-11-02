Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 切換到腳本目錄
WshShell.CurrentDirectory = scriptDir

' 執行 setup_env.py（如果有問題會跳過）
On Error Resume Next
WshShell.Run "python setup_env.py", 0, True
On Error Goto 0

' 執行 app.py（顯示視窗）
WshShell.Run "python app.py", 1, False
Set WshShell = Nothing
Set fso = Nothing

