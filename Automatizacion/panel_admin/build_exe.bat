@echo off
REM Opcional: genera un PanelAdmin.exe standalone en la carpeta dist/.
REM Igual necesitás Python instalado en la PC para que el .exe pueda
REM lanzar piloto_automatico.py y bot_whatsapp.py (ellos siguen siendo
REM scripts .py normales). Esto solo empaqueta el panel en sí.

cd /d "%~dp0"
pip install pyinstaller >nul
pyinstaller --onefile --noconsole --name PanelAdmin ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    app.py

echo.
echo Listo. El ejecutable quedo en dist\PanelAdmin.exe
echo Copialo (junto con esta carpeta si queres conservar el codigo) a
echo automatizacion\panel_admin\ dentro de tu repo, y ejecutalo con doble clic.
pause
