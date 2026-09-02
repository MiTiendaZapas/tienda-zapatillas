' Lanza piloto_automatico.py oculto, en segundo plano, sin ventana de
' consola (a través de piloto_wrapper.py, que además guarda el PID en
' piloto.pid y manda toda la salida a piloto_log.txt).
'
' Pensado para el acceso directo del Escritorio "Piloto Automatico".
' Para detenerlo, usá detener_piloto.bat (no hay ventana para cerrar
' con la X).
'
' Si preferís verlo correr en vivo en una consola (por ejemplo para
' confirmar que anda bien la primera vez), usá en cambio
' piloto_automatico_visible.bat.

Dim objFSO, objShell, scriptDir

Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = scriptDir

objShell.Run "cmd /c python piloto_wrapper.py", 0, False
