@echo off
cd /d "%~dp0"
title Bot WhatsApp - VINCULAR DE NUEVO (codigo QR)
echo La sesion de WhatsApp Web vencio. Se abre una sesion NUEVA con un codigo QR.
echo En el celular del bot: WhatsApp ^> Dispositivos vinculados ^> Vincular un dispositivo, y escanear el QR.
echo No cerrar la ventana de WhatsApp hasta que este programa diga que termino.
echo Es el mismo numero de siempre: la sesion vieja queda guardada en sesion_wsp_anterior.
echo.
python vincular_whatsapp_nuevo.py
if errorlevel 1 (
  echo.
  echo No se pudo cambiar la sesion: el bot NO se reinicia. Volver a abrir este archivo.
  pause
  exit /b 1
)
echo.
echo Sesion nueva lista. Vuelvo al modo programado...
title Bot WhatsApp - programado (manda solo todos los dias)
python bot_whatsapp.py
echo.
pause
