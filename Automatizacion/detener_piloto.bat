@echo off
title Detener Piloto Automatico
cd /d "%~dp0"

if not exist piloto.pid (
    echo El Piloto Automatico no parece estar corriendo ^(no se encontro piloto.pid^).
    echo Si crees que si esta corriendo, abri el Administrador de tareas,
    echo pestana "Detalles", busca "python.exe" y termina el proceso a mano
    echo ^(fijate la fecha/hora de inicio si tenes mas de un python.exe^).
    pause
    exit /b
)

set /p PID=<piloto.pid
taskkill /F /PID %PID% >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Piloto Automatico detenido correctamente.
) else (
    echo No se pudo detener el proceso %PID% ^(puede que ya estuviera apagado^).
)

del piloto.pid >nul 2>&1
pause
