"""Cambia el número de WhatsApp con el que manda el bot, sin tocar el actual hasta que el nuevo esté verificado.

Qué hace:
  1. Abre WhatsApp Web en una sesión NUEVA (carpeta sesion_wsp_nueva) y muestra el código QR.
  2. Esperá a escanearlo desde el celular del número nuevo:
     WhatsApp > Dispositivos vinculados > Vincular un dispositivo.
  3. Deja que WhatsApp termine de sincronizar y comprueba (sin mandar nada) que el número nuevo
     encuentre los grupos «Equipo de trabajo» y «Notas Whassap» (tiene que estar agregado a los dos).
  4. Si el grupo real aparece, guarda la sesión vieja como sesion_wsp_anterior y deja la nueva como
     sesion_wsp, que es la que usa el bot. Si no aparece, no cambia nada.

Para volver al número anterior: cerrar el bot, y renombrar las carpetas sesion_wsp <-> sesion_wsp_anterior.
Si algo se corta, se puede volver a correr: la sesión nueva queda vinculada y no pide el QR de nuevo.
"""
import importlib.util
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
AQUI = Path(__file__).resolve().parent
ACTUAL = AQUI / "sesion_wsp"
NUEVA = AQUI / "sesion_wsp_nueva"
ANTERIOR = AQUI / "sesion_wsp_anterior"
ESPERA_QR_MIN = 10          # cuánto se espera a que escanees el código
ESPERA_SINCRONIZAR_MIN = 15


def cargar_bot():
    spec = importlib.util.spec_from_file_location("bot_whatsapp", AQUI / "bot_whatsapp.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main():
    bot = cargar_bot()
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print(" CAMBIO DE NÚMERO DE WHATSAPP DEL BOT")
    print("=" * 60)
    print("Se va a abrir una ventana de WhatsApp Web con un código QR.")
    print("En el celular del número NUEVO: WhatsApp > Dispositivos vinculados > Vincular un dispositivo,")
    print("y escaneá el código. No cierres la ventana hasta que este programa diga que terminó.\n")

    grupos_ok = {}
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(user_data_dir=str(NUEVA), headless=False)
        try:
            page = contexto.pages[0] if contexto.pages else contexto.new_page()
            page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=90000)
            inicio, ultimo_aviso = time.time(), 0
            while not page.locator("#pane-side").count():
                if time.time() - inicio > ESPERA_QR_MIN * 60:
                    print(f"❌ Pasaron {ESPERA_QR_MIN} minutos sin vincular. Volvé a abrir este programa cuando estés listo.")
                    return 1
                if time.time() - ultimo_aviso > 30:
                    ultimo_aviso = time.time()
                    print("⏳ Esperando que escanees el código QR (o que cargue la lista de chats)...")
                page.wait_for_timeout(2000)
            print("✅ Número vinculado. Dejo que WhatsApp termine de sincronizar (puede tardar unos minutos)...")

            inicio = time.time()
            while page.locator('[data-testid="wa-web-loading-screen"]').count():
                if time.time() - inicio > ESPERA_SINCRONIZAR_MIN * 60:
                    break
                page.wait_for_timeout(3000)
            page.wait_for_timeout(90 * 1000)

            for etiqueta, nombre in (("real", bot.GRUPO_REAL), ("de prueba", bot.GRUPO_PRUEBA)):
                if not nombre:
                    continue
                try:
                    bot.abrir_grupo(page, nombre)
                    grupos_ok[etiqueta] = True
                    print(f"✅ Grupo {etiqueta} «{nombre}»: encontrado con el número nuevo.")
                except Exception as error:
                    grupos_ok[etiqueta] = False
                    print(f"❌ Grupo {etiqueta} «{nombre}»: NO lo encuentro con el número nuevo ({error}).")
        finally:
            contexto.close()

    if not grupos_ok.get("real"):
        print("\n⚠️ NO cambié nada: el número nuevo todavía no está en el grupo real.")
        print("   Agregalo al grupo «%s» y volvé a abrir este programa (no te va a pedir el QR de nuevo)." % bot.GRUPO_REAL)
        return 2

    print("\nCambiando la sesión del bot...")
    try:
        if ANTERIOR.exists():
            shutil.move(str(ANTERIOR), str(AQUI / f"sesion_wsp_anterior_{datetime.now():%Y%m%d_%H%M%S}"))
        if ACTUAL.exists():
            ACTUAL.rename(ANTERIOR)
        NUEVA.rename(ACTUAL)
    except OSError as error:
        print(f"❌ No pude renombrar las carpetas ({error}).")
        print("   Probablemente el bot está usando WhatsApp en este momento. Esperá a que termine y volvé a correr esto.")
        return 3

    print("✅ LISTO: el bot va a mandar con el número nuevo desde el próximo envío.")
    if not grupos_ok.get("de prueba"):
        print("ℹ️ El número nuevo no está en el grupo de prueba: las pruebas con --prueba no van a andar hasta que lo agregues.")
    print("   (El número anterior quedó guardado en sesion_wsp_anterior.)")
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except KeyboardInterrupt:
        print("Cancelado.")
        codigo = 1
    input("\nApretá ENTER para cerrar esta ventana... ")
    sys.exit(codigo)
