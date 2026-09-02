@echo off
title Panel Admin - Tienda Zapas
cd /d "%~dp0"

echo Instalando/actualizando dependencias (solo tarda la primera vez)...
pip install -r requirements.txt >nul 2>&1

echo.
echo Iniciando el Panel Admin...
echo (Esta ventana tiene que quedar abierta mientras usas el panel. Se abre solo en el navegador.)
echo.

python app.py

pause
