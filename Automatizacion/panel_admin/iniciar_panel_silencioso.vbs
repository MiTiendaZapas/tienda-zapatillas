' Lanza el Panel Admin (app.py) completamente oculto, sin ventana de
' consola. Pensado para el acceso directo del Escritorio.
'
' Si algo no arranca y necesitás ver el error, usá en cambio
' iniciar_panel.bat (ese sí muestra la consola).

Dim objFSO, objShell, scriptDir

Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = scriptDir

' El 0 = ventana oculta. El False = no esperar a que termine (arranca y sigue).
objShell.Run "cmd /c python app.py", 0, False
