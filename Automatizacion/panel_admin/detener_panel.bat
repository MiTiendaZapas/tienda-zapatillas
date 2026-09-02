@echo off
title Detener Panel Admin
cd /d "%~dp0"

if not exist panel.pid (
    echo El Panel Admin no parece estar corriendo ^(no se encontro panel.pid^).
    echo Si crees que si esta corriendo, abri el Administrador de tareas,
    echo pestana "Detalles", busca "python.exe" y termina el proceso a mano.
    pause
    exit /b
)

set /p PID=<panel.pid
taskkill /F /PID %PID% >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Panel Admin detenido correctamente.
) else (
    echo No se pudo detener el proceso %PID% ^(puede que ya estuviera apagado^).
)

del panel.pid >nul 2>&1
pause
