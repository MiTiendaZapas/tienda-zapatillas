@echo off
title Bot WhatsApp - Tienda Zapas

REM bot_whatsapp.py necesita correr parado en la RAIZ del repo, igual
REM que el piloto (usa rutas relativas tipo "Fotos/" y "stock_proveedor.txt").
cd /d "%~dp0.."

echo Bot de WhatsApp - Tienda Zapas
echo.
echo OJO: este bot pide un paso manual (adjuntar a mano la primera foto
echo y confirmar). Por eso esta ventana NO puede ocultarse: la necesitas
echo para escribir/confirmar ahi cuando te lo pida.
echo.

python automatizacion\bot_whatsapp.py

pause
