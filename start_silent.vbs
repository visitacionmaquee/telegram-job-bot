Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run Chr(34) & ".venv\Scripts\pythonw.exe" & Chr(34) & " bot.py", 0
Set WshShell = Nothing
