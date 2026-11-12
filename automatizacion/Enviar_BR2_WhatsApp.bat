@echo off
cd /d "%~dp0"
title Bot WhatsApp - mandando zapatillas BR de la segunda tienda (talles BR)
echo Mando al grupo REAL solo las zapatillas BR de la segunda tienda, aclarando que son talles BR.
echo Si se corta, volver a abrir este archivo: no repite lo ya enviado del dia.
echo Cuando termina, el bot vuelve solo al modo programado (en esta misma ventana).
echo Antes de abrirlo hay que CERRAR el bot programado, porque no pueden estar los dos a la vez.
echo.
python bot_whatsapp.py --solo-br2
echo.
echo Listo. Vuelvo al modo programado...
title Bot WhatsApp - programado (manda solo todos los dias)
python bot_whatsapp.py
echo.
pause
