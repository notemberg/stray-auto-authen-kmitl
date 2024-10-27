Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
pythonScriptPath = scriptDir & "\stray_auto_authen.pyw"

WshShell.Run pythonScriptPath, 0, False