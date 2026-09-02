@echo off
title Piloto Automatico - Tienda Zapas

REM piloto_automatico.py necesita correr parado en la RAIZ del repo
REM (usa rutas relativas tipo "Fotos/" y "catalogo.js"), por eso
REM subimos una carpeta antes de llamarlo.
cd /d "%~dp0.."

echo Corriendo piloto_automatico.py en modo visible.
echo Cerra esta ventana (o Ctrl+C) para detenerlo.
echo.

python automatizacion\piloto_automatico.py

pause
