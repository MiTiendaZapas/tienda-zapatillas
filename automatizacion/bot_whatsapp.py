"""Bot de WhatsApp: manda el stock del catálogo a un grupo, todos los días a una hora al azar.

Lee el catálogo que ya mantiene el piloto (catalogo/productos.json de
mitiendazapas.github.io): no scrapea al proveedor.

Modos:
    python bot_whatsapp.py                    programado: cada día a una hora al azar (HORA_DESDE..HORA_HASTA)
    python bot_whatsapp.py --prueba           manda 3 modelos + el mensaje de precios al GRUPO DE PRUEBA
    python bot_whatsapp.py --prueba --limite 10
    python bot_whatsapp.py --ahora            manda ya mismo al grupo real (y cuenta como el envío de hoy)
    python bot_whatsapp.py --dry-run          arma los mensajes y los muestra, sin abrir WhatsApp
    python bot_whatsapp.py --diagnostico      abre WhatsApp y el grupo de prueba, saca una captura; NO manda nada
    (--paso-manual: vuelve al paso viejo de mandar a mano la primera foto)
"""
import argparse
import json
import os
import random
import re
import sys
import threading
import time
import unicodedata
import urllib.request
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image
import win32clipboard
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Fuerza UTF-8 en la salida: en Windows la consola suele usar cp1252, que no
# sabe representar los emojis y haría crashear el script.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def _deshabilitar_quickedit_windows():
    # Un clic en la consola activa "QuickEdit Mode" y CONGELA el script hasta
    # apretar Enter. Como este bot corre solo, se desactiva. Todo lo que se
    # imprime queda también en automatizacion/logs/bot_whatsapp.log.
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)
        modo = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(modo)):
            kernel32.SetConsoleMode(handle, (modo.value & ~0x0040) | 0x0080)
    except Exception:
        pass


_deshabilitar_quickedit_windows()

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# --- LOG A ARCHIVO -----------------------------------------------------------
import logging
from logging.handlers import RotatingFileHandler


def _configurar_log_a_archivo(nombre_archivo):
    carpeta = SCRIPT_DIR / "logs"
    carpeta.mkdir(exist_ok=True)
    handler = RotatingFileHandler(carpeta / nombre_archivo, maxBytes=5_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger = logging.getLogger(nombre_archivo)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class _CopiarSalidaALog:
    def __init__(self, flujo, logger):
        self._flujo, self._logger, self._pendiente = flujo, logger, ""

    def write(self, texto):
        self._flujo.write(texto)
        self._pendiente += texto
        while "\n" in self._pendiente:
            linea, self._pendiente = self._pendiente.split("\n", 1)
            if linea.strip():
                self._logger.info(linea)
        return len(texto)

    def flush(self):
        self._flujo.flush()

    def __getattr__(self, nombre):
        return getattr(self._flujo, nombre)


try:
    _logger_bot = _configurar_log_a_archivo("bot_whatsapp.log")
    sys.stdout = _CopiarSalidaALog(sys.stdout, _logger_bot)
    sys.stderr = _CopiarSalidaALog(sys.stderr, _logger_bot)
except Exception:
    pass

# --- CONFIGURACIÓN -------------------------------------------------------------
GRUPO_PRUEBA = "Notas Whassap"
GRUPO_REAL = None                 # se completa cuando la prueba salga bien

HORA_DESDE = (7, 45)              # cada día se sortea una hora entre estas dos
HORA_HASTA = (8, 10)
TOLERANCIA_TARDE_MIN = 120        # si la laptop estaba apagada a esa hora, se manda igual hasta 2 h después
MAX_INTENTOS_DIA = 3
ESPERA_ENTRE_INTENTOS_MIN = 15
LIMITE_CARGA_MIN = 20             # tiempo máximo que se espera a que WhatsApp Web termine de sincronizar
ESPERA_CATALOGO_FRESCO_MIN = 30   # el piloto arranca a las 7:30: se espera a que publique su primera vuelta
CATALOGO_FRESCO_DESDE = (7, 30)

URL_CATALOGO = "https://mitiendazapas.github.io/catalogo/productos.json"
URL_BASE_CATALOGO = "https://mitiendazapas.github.io/catalogo/"
CATALOGO_LOCAL = REPO_ROOT.parent / "mitiendazapas.github.io" / "catalogo"   # copia que mantiene el piloto en esta laptop
CACHE_FOTOS = SCRIPT_DIR / "_cache_fotos"
ARCHIVO_ESTADO = SCRIPT_DIR / "estado_bot.json"
PAUSA_ENTRE_ENVIOS = (5, 15)      # segundos, al azar
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# Mensaje de precios que se manda como texto, UNA vez, después de las fotos.
# Es texto fijo: si cambian los precios hay que actualizarlo acá a mano.
MENSAJE_FINAL_PRECIOS = (
    "Zapatillas calidad Brasil 🇧🇷 (primera línea,luxo)\n"
    "Talles de adulto $43.000 por unidad ‼️\n"
    "🔥 A PARTIR DE 5 unidades te quedan en $37.000/$39.000/$41.000 🔥\n"
    "🚨 TALLE NIÑO $35.000c/u 🚨\n"
    "Por mayor $30.000c/u ‼️\n"
    "🚨OJOTAS $35.000c/u🚨\n"
    "Por mayor $31.000c/u‼️\n"
    "🚨 OJOTAS  MIND  $37.000c/u🚨\n"
    "Por mayor $35.000c/u ‼️\n"
    "🚨 JORDAN 11 Y RETRO 11 PANDA $55.000c/u 🚨\n"
    "Por mayor $50.000c/u ‼️"
)


class SesionVencida(Exception):
    """WhatsApp Web pide vincular de nuevo (código QR)."""


class GrupoNoEncontrado(Exception):
    """No se pudo abrir el grupo, o el chat abierto no es el que corresponde."""


class EnvioBloqueado(Exception):
    """WhatsApp no está aceptando los envíos automáticos."""


def avisar(titulo, texto):
    """Deja constancia visible de un problema que necesita atención."""
    print(f"🚨 {titulo}: {texto}")
    try:
        (SCRIPT_DIR / "logs" / "ATENCION_bot.txt").write_text(
            f"{datetime.now():%Y-%m-%d %H:%M} {titulo}\n{texto}\n", encoding="utf-8")
        import ctypes
        threading.Thread(target=lambda: ctypes.windll.user32.MessageBoxW(0, texto, titulo, 0x10 | 0x40000),
                         daemon=True).start()
    except Exception:
        pass


# --- Una sola copia del bot a la vez (evita mandar todo duplicado) -------------
def tomar_candado_unico():
    import ctypes
    ctypes.windll.kernel32.SetLastError(0)
    candado = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\BotWhatsAppTiendaZapatillas")
    if ctypes.windll.kernel32.GetLastError() == 183:      # ERROR_ALREADY_EXISTS
        return None
    return candado


# --- Catálogo ------------------------------------------------------------------
def _descargar(url, timeout=30, reintentos=3):
    for intento in range(1, reintentos + 1):
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(pedido, timeout=timeout) as respuesta:
                return respuesta.read()
        except Exception:
            if intento == reintentos:
                raise
            time.sleep(5 * intento)


def cargar_catalogo():
    """Devuelve (catalogo, origen). Primero la web publicada; si falla, la copia local del piloto."""
    try:
        datos = json.loads(_descargar(f"{URL_CATALOGO}?t={int(time.time())}").decode("utf-8"))
        origen = "web"
    except Exception as error:
        local = CATALOGO_LOCAL / "productos.json"
        if not local.exists():
            raise RuntimeError(f"No pude leer el catálogo de la web ({error}) y tampoco hay copia local.")
        print(f"⚠️ Catálogo de la web no disponible ({error}); uso la copia local.")
        datos = json.loads(local.read_text(encoding="utf-8"))
        origen = "copia local"
    if not datos.get("products"):
        raise RuntimeError("El catálogo está vacío: no se manda nada.")
    return datos, origen


def _edad_catalogo(catalogo):
    return datetime.now().astimezone() - datetime.fromisoformat(catalogo["generatedAt"])


def esperar_catalogo_fresco():
    """Si el piloto todavía no publicó su primera vuelta del día, se espera un rato."""
    limite = time.time() + ESPERA_CATALOGO_FRESCO_MIN * 60
    desde = datetime.now().astimezone().replace(hour=CATALOGO_FRESCO_DESDE[0], minute=CATALOGO_FRESCO_DESDE[1],
                                                second=0, microsecond=0)
    while True:
        catalogo, origen = cargar_catalogo()
        if datetime.fromisoformat(catalogo["generatedAt"]) >= desde:
            return catalogo, origen
        if time.time() >= limite:
            print(f"⚠️ El catálogo es de {catalogo['generatedAt']} (el piloto no publicó la vuelta de hoy): "
                  "se manda con ese stock.")
            return catalogo, origen
        print("⏳ Esperando que el piloto publique el catálogo de hoy...")
        time.sleep(120)


def formatear_talles(sizes):
    """Solo talles con stock. Si hay 4 o más seguidos se resumen ("34 al 38"); los pares de ojotas ("39/40") van tal cual."""
    con_stock = [s["size"] for s in sizes if s["stock"] > 0]
    if not con_stock:
        return None
    numericos = sorted({int(t) for t in con_stock if t.isdigit()})
    otros = sorted((t for t in con_stock if not t.isdigit()),
                   key=lambda t: float(re.findall(r"\d+", t)[0]) if re.findall(r"\d+", t) else 999)
    partes, grupo = [], []
    for numero in numericos + [None]:
        if grupo and (numero is None or numero != grupo[-1] + 1):
            partes.extend([f"{grupo[0]} al {grupo[-1]}"] if len(grupo) >= 4 else [str(n) for n in grupo])
            grupo = []
        if numero is not None:
            grupo.append(numero)
    return ", ".join(partes + otros)


def armar_productos(catalogo):
    """Lista de {id, name, texto, foto} en el orden del catálogo (stock de casa primero)."""
    productos = []
    for producto in catalogo["products"]:
        talles = formatear_talles(producto["sizes"])
        if talles is None or not producto.get("images"):
            continue
        productos.append({
            "id": producto["id"], "name": producto["name"],
            "texto": f"{producto['name']}\n{talles}", "foto": producto["images"][0]["lg"],
        })
    return productos


def obtener_foto(ruta_relativa):
    """Ruta local de la foto: la copia del piloto si existe (los nombres llevan hash, no cambian), si no se baja."""
    local = CATALOGO_LOCAL / ruta_relativa
    if local.exists():
        return local
    destino = CACHE_FOTOS / ruta_relativa.replace("/", "__")
    if not destino.exists():
        CACHE_FOTOS.mkdir(exist_ok=True)
        temporal = destino.with_name(destino.name + f".{os.getpid()}.part")
        temporal.write_bytes(_descargar(URL_BASE_CATALOGO + ruta_relativa))
        os.replace(temporal, destino)
    return destino


def copiar_imagen_al_portapapeles(ruta_imagen):
    imagen = Image.open(ruta_imagen)
    salida = BytesIO()
    imagen.convert("RGB").save(salida, "BMP")
    datos = salida.getvalue()[14:]
    for intento in range(1, 6):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, datos)
            finally:
                win32clipboard.CloseClipboard()
            return
        except Exception:
            if intento == 5:
                raise
            time.sleep(0.5)


# --- WhatsApp Web ----------------------------------------------------------------
def _norm(texto):
    texto = unicodedata.normalize("NFKD", texto or "").casefold()
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def _solo_alfanumerico(texto):
    return " ".join(re.sub(r"[\W_]+", " ", _norm(texto)).split())


def _goto_con_reintentos(page, url, intentos=3, espera_seg=15, **kwargs):
    for intento in range(1, intentos + 1):
        try:
            return page.goto(url, **kwargs)
        except Exception as error:
            if intento == intentos:
                raise
            print(f"  ⚠️ No se pudo abrir {url} (intento {intento}/{intentos}): {error}. Reintento en {espera_seg}s...")
            time.sleep(espera_seg)


def abrir_whatsapp(p):
    try:
        contexto = p.chromium.launch_persistent_context(user_data_dir=str(SCRIPT_DIR / "sesion_wsp"), headless=False)
    except Exception as error:
        raise RuntimeError(f"No pude abrir el perfil de WhatsApp ({error}). ¿Quedó otra ventana del bot abierta?")
    page = contexto.pages[0] if contexto.pages else contexto.new_page()
    try:
        print("Abriendo WhatsApp Web...")
        _goto_con_reintentos(page, "https://web.whatsapp.com/")
        _esperar_lista_de_chats(page)
    except Exception:
        contexto.close()
        raise
    return contexto, page


def _esperar_lista_de_chats(page):
    """Espera a que WhatsApp Web muestre los chats. Distingue tres situaciones:
    - cargó la lista de chats: listo;
    - muestra el código QR: la sesión venció, hay que volver a vincular (aviso inmediato);
    - "Cargando tus chats" (re-sincroniza el historial, lento en esta laptop): se espera hasta
      LIMITE_CARGA_MIN, sin cerrar la ventana, porque cerrarla corta la sincronización."""
    inicio = time.time()
    ultimo_aviso = 0
    while True:
        if page.locator("#pane-side").count():
            return
        cargando = page.locator('[data-testid="wa-web-loading-screen"]').count() > 0
        if not cargando and page.locator("canvas").count() and time.time() - inicio > 15:
            raise SesionVencida("WhatsApp Web pide el código QR: la sesión venció. "
                                "Hay que volver a vincular el teléfono abriendo el bot a mano.")
        limite = LIMITE_CARGA_MIN * 60 if cargando else 90
        if time.time() - inicio > limite:
            raise RuntimeError(f"WhatsApp Web no terminó de cargar en {limite // 60} min "
                               f"({'sigue sincronizando' if cargando else 'no mostró ni chats ni QR'}).")
        if time.time() - ultimo_aviso > 60:
            ultimo_aviso = time.time()
            texto = ""
            try:
                texto = page.locator('[data-testid="wa-web-loading-screen"]').first.inner_text(timeout=1000).replace("\n", " ")
            except Exception:
                pass
            print(f"⏳ WhatsApp Web cargando... {texto[:60]}")
        page.wait_for_timeout(2000)


def _chat_abierto(page):
    """Nombre normalizado del chat abierto (o None)."""
    try:
        titulo = page.locator('#main header [data-testid="conversation-info-header-chat-title"]').first.inner_text(timeout=2000)
        return _norm(titulo)
    except Exception:
        return None


def abrir_grupo(page, nombre):
    """Abre el grupo buscándolo por nombre y comprueba que el chat abierto sea ESE grupo."""
    objetivo = _norm(nombre)
    if _chat_abierto(page) == objetivo:
        return
    page.keyboard.press("Control+Alt+/")                 # atajo de WhatsApp Web: foco en el buscador
    page.wait_for_timeout(600)
    page.keyboard.insert_text(nombre)
    page.wait_for_timeout(2000)
    coincidencias = [c for c in page.locator("#pane-side span[title]").all()
                     if _norm(c.get_attribute("title")) == objetivo]
    if not coincidencias:
        page.keyboard.press("Escape")
        raise GrupoNoEncontrado(f"No encontré ningún chat llamado exactamente «{nombre}».")
    if len(coincidencias) > 1:
        page.keyboard.press("Escape")
        raise GrupoNoEncontrado(f"Hay {len(coincidencias)} chats llamados «{nombre}»: no sé a cuál mandar, no mando nada.")
    coincidencias[0].click()
    page.wait_for_timeout(1500)
    if _chat_abierto(page) != objetivo:
        raise GrupoNoEncontrado(f"Abrí un chat distinto de «{nombre}»: no mando nada.")


def _ultima_fila(page):
    """(data-id, texto) del último mensaje visible del chat abierto; (None, '') si no se puede leer."""
    try:
        fila = page.locator("#main [data-id]").last
        return fila.get_attribute("data-id", timeout=1500), fila.inner_text(timeout=1500)
    except Exception:
        return None, ""


def esperar_envio_nuevo(page, id_anterior, texto_esperado, timeout_seg=25):
    """True cuando aparece una fila nueva al final del chat que contiene el texto que mandamos."""
    # Se comparan solo letras y números: WhatsApp dibuja los emojis como imágenes y no
    # aparecen en el texto leído de la página (el mensaje salía bien pero no se reconocía).
    esperado = _solo_alfanumerico(texto_esperado.split("\n")[0])
    fin = time.time() + timeout_seg
    while time.time() < fin:
        id_actual, texto = _ultima_fila(page)
        if id_actual and id_actual != id_anterior and esperado in _solo_alfanumerico(texto):
            return True
        page.wait_for_timeout(500)
    return False


def esperar_envios_pendientes(page, timeout_seg=120):
    """Antes de cerrar el navegador, espera a que ningún mensaje reciente siga con el relojito de 'enviando'."""
    fin = time.time() + timeout_seg
    while time.time() < fin:
        if page.locator('#main [data-icon="msg-time"]').count() == 0:
            return True
        page.wait_for_timeout(1000)
    print("⚠️ Quedaron mensajes todavía 'enviándose' al cerrar.")
    return False


def _escribir_y_enviar(page, texto):
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        page.keyboard.insert_text(linea)
        if i < len(lineas) - 1:
            page.keyboard.press("Shift+Enter")
    page.wait_for_timeout(1000)
    page.keyboard.press("Enter")


def enviar_foto_con_texto(page, producto):
    foto = obtener_foto(producto["foto"])
    copiar_imagen_al_portapapeles(foto)
    id_anterior, _ = _ultima_fila(page)
    caja = page.locator('div[contenteditable="true"]').last
    caja.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+V")
    page.wait_for_timeout(3500)
    _escribir_y_enviar(page, producto["texto"])
    return esperar_envio_nuevo(page, id_anterior, producto["texto"])


def enviar_texto(page, texto):
    id_anterior, _ = _ultima_fila(page)
    page.locator('div[contenteditable="true"]').last.click()
    page.wait_for_timeout(500)
    _escribir_y_enviar(page, texto)
    return esperar_envio_nuevo(page, id_anterior, texto)


def enviar_tanda(p, grupo, productos, estado=None, guardar=None, paso_manual=False):
    """Manda los productos (los que falten, si hay estado) y el mensaje de precios. Devuelve un resumen."""
    ya = set(estado["enviados"]) if estado else set()
    pendientes = [x for x in productos if x["id"] not in ya]
    enviados = fallidos = seguidas = 0
    precios = bool(estado and estado.get("precios_enviados"))
    print(f"📨 Grupo «{grupo}»: {len(pendientes)} por mandar ({len(ya)} ya enviados antes).")

    contexto, page = abrir_whatsapp(p)
    try:
        abrir_grupo(page, grupo)
        for numero, producto in enumerate(pendientes, 1):
            abrir_grupo(page, grupo)                       # vuelve a comprobar que sea el grupo correcto
            if paso_manual and enviados == 0 and not ya:
                print(f"\n🛑 PASO MANUAL: mandá a mano la foto de «{producto['name']}» con este texto:\n{producto['texto']}")
                input("👉 Cuando esté ENVIADA, apretá ENTER acá: ")
                ok = True
            else:
                ok = False
                for intento in (1, 2):
                    try:
                        ok = enviar_foto_con_texto(page, producto)
                    except Exception as error:
                        print(f"  ⚠️ {producto['name']} (intento {intento}): {error}")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                    if ok:
                        break
            if ok:
                enviados += 1
                seguidas = 0
                if estado is not None:
                    estado["enviados"].append(producto["id"])
                    guardar()
                pausa = random.uniform(*PAUSA_ENTRE_ENVIOS)
                print(f"✅ [{numero}/{len(pendientes)}] {producto['name']}. Pausa de {pausa:.0f}s...")
                time.sleep(pausa)
            else:
                fallidos += 1
                seguidas += 1
                print(f"❌ [{numero}/{len(pendientes)}] {producto['name']}: no salió.")
                if enviados == 0 and seguidas >= 2:
                    raise EnvioBloqueado("WhatsApp no aceptó el primer envío automático. "
                                         "Puede hacer falta el paso manual (--paso-manual).")
                if seguidas >= 3:
                    raise EnvioBloqueado("Fallaron 3 envíos seguidos: se corta para no seguir a ciegas.")

        if not precios:
            abrir_grupo(page, grupo)
            print("Mandando el mensaje final de precios...")
            if enviar_texto(page, MENSAJE_FINAL_PRECIOS):
                precios = True
                if estado is not None:
                    estado["precios_enviados"] = True
                    guardar()
                print("✅ Mensaje de precios enviado.")
            else:
                print("❌ El mensaje de precios no salió.")
        esperar_envios_pendientes(page)
    finally:
        contexto.close()
    return {"enviados": enviados, "fallidos": fallidos, "precios": precios}


# --- Estado diario -----------------------------------------------------------------
def cargar_estado():
    try:
        return json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_estado(estado):
    temporal = ARCHIVO_ESTADO.with_suffix(".tmp")
    temporal.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporal, ARCHIVO_ESTADO)


def sortear_hora():
    inicio = HORA_DESDE[0] * 3600 + HORA_DESDE[1] * 60
    fin = HORA_HASTA[0] * 3600 + HORA_HASTA[1] * 60
    segundos = random.randint(inicio, fin)
    return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"


def estado_de_hoy(forzar_ahora=False):
    hoy = datetime.now().date().isoformat()
    estado = cargar_estado()
    if estado.get("dia") != hoy:
        estado = {"dia": hoy, "hora": sortear_hora(), "enviados": [], "precios_enviados": False,
                  "terminado": False, "intentos": 0, "resultado": None}
        print(f"📅 Hoy ({hoy}) el bot manda a las {estado['hora']}.")
    if forzar_ahora and not estado["terminado"]:
        estado["hora"] = datetime.now().strftime("%H:%M:%S")
    guardar_estado(estado)
    return estado


def ejecutar_envio_real(estado):
    """Un intento de envío al grupo real. Actualiza el estado según resultado."""
    estado["intentos"] += 1
    guardar_estado(estado)
    try:
        catalogo, origen = esperar_catalogo_fresco()
        productos = armar_productos(catalogo)
        print(f"📚 Catálogo de {origen} ({catalogo['generatedAt']}): {len(productos)} modelos para mandar.")
        with sync_playwright() as p:
            resumen = enviar_tanda(p, GRUPO_REAL, productos, estado, lambda: guardar_estado(estado))
        estado["terminado"] = True
        estado["resultado"] = f"OK: {resumen['enviados']} enviados, {resumen['fallidos']} fallidos, precios={resumen['precios']}"
        if resumen["fallidos"]:
            avisar("Bot de WhatsApp", f"Terminó, pero {resumen['fallidos']} modelo(s) no salieron. Revisá el log.")
        print(f"🏁 {estado['resultado']}")
    except (SesionVencida, GrupoNoEncontrado, EnvioBloqueado) as error:
        estado["terminado"] = True
        estado["resultado"] = f"ERROR: {error}"
        avisar("Bot de WhatsApp: necesita atención", str(error))
    except Exception as error:
        print(f"❌ Intento {estado['intentos']}/{MAX_INTENTOS_DIA} falló: {type(error).__name__}: {error}")
        if estado["intentos"] >= MAX_INTENTOS_DIA:
            estado["terminado"] = True
            estado["resultado"] = f"ERROR tras {MAX_INTENTOS_DIA} intentos: {error}"
            avisar("Bot de WhatsApp: no pudo mandar hoy", str(error))
        else:
            print(f"Reintento en {ESPERA_ENTRE_INTENTOS_MIN} min (lo ya enviado no se repite).")
            guardar_estado(estado)
            time.sleep(ESPERA_ENTRE_INTENTOS_MIN * 60)
    guardar_estado(estado)


def ciclo_diario():
    ahora = datetime.now()
    estado = estado_de_hoy()
    if estado["terminado"]:
        manana = (ahora + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        time.sleep(max(60, min((manana - ahora).total_seconds(), 3600)))
        return
    h, m, s = map(int, estado["hora"].split(":"))
    objetivo = ahora.replace(hour=h, minute=m, second=s, microsecond=0)
    if ahora < objetivo:
        time.sleep(max(1, min((objetivo - ahora).total_seconds(), 600)))
        return
    if ahora > objetivo + timedelta(minutes=TOLERANCIA_TARDE_MIN) and estado["intentos"] == 0:
        estado["terminado"] = True
        estado["resultado"] = "Omitido: la laptop estaba apagada o dormida a la hora programada."
        guardar_estado(estado)
        avisar("Bot de WhatsApp", estado["resultado"])
        return
    ejecutar_envio_real(estado)


# --- Modos ----------------------------------------------------------------------------
def modo_programado(ahora=False):
    if not GRUPO_REAL:
        print("❌ Falta configurar GRUPO_REAL en bot_whatsapp.py (todavía solo está el grupo de prueba).")
        return 2
    print(f"🤖 Bot de WhatsApp programado: manda a «{GRUPO_REAL}» cada día entre "
          f"{HORA_DESDE[0]:02d}:{HORA_DESDE[1]:02d} y {HORA_HASTA[0]:02d}:{HORA_HASTA[1]:02d}.")
    if ahora:
        ejecutar_envio_real(estado_de_hoy(forzar_ahora=True))
        return 0
    while True:
        try:
            ciclo_diario()
        except KeyboardInterrupt:
            raise
        except Exception as error:
            print(f"❌ Error inesperado en el ciclo diario: {type(error).__name__}: {error}")
            time.sleep(300)


def modo_prueba(limite, paso_manual):
    catalogo, origen = cargar_catalogo()
    productos = armar_productos(catalogo)
    if limite:
        productos = productos[:limite]
    print(f"🧪 PRUEBA en «{GRUPO_PRUEBA}»: {len(productos)} modelos (catálogo de {origen}, {catalogo['generatedAt']}).")
    with sync_playwright() as p:
        resumen = enviar_tanda(p, GRUPO_PRUEBA, productos, paso_manual=paso_manual)
    print(f"🏁 Prueba terminada: {resumen}")
    return 0 if not resumen["fallidos"] and resumen["precios"] else 1


def modo_dry_run():
    catalogo, origen = cargar_catalogo()
    productos = armar_productos(catalogo)
    print(f"Catálogo de {origen} ({catalogo['generatedAt']}, hace {_edad_catalogo(catalogo)}): "
          f"{len(catalogo['products'])} productos, {len(productos)} para mandar.")
    for producto in productos[:3]:
        print("-" * 40)
        print(producto["texto"])
        print("foto:", obtener_foto(producto["foto"]))
    print("-" * 40)
    print(f"Grupo de prueba: «{GRUPO_PRUEBA}» | grupo real: {GRUPO_REAL!r} | "
          f"ventana diaria {HORA_DESDE[0]:02d}:{HORA_DESDE[1]:02d}-{HORA_HASTA[0]:02d}:{HORA_HASTA[1]:02d}")
    return 0


def modo_diagnostico():
    with sync_playwright() as p:
        contexto, page = abrir_whatsapp(p)
        try:
            print("✅ WhatsApp Web cargó la lista de chats (la sesión está vinculada).")
            abrir_grupo(page, GRUPO_PRUEBA)
            print(f"✅ Grupo «{GRUPO_PRUEBA}» abierto y verificado por el título.")
            print("Cajas de texto (contenteditable):", page.locator('div[contenteditable="true"]').count())
            print("Mensajes visibles en el chat (data-id):", page.locator("#main [data-id]").count())
            captura = SCRIPT_DIR / "logs" / "diagnostico_whatsapp.png"
            page.screenshot(path=str(captura))
            print("Captura:", captura)
        finally:
            contexto.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prueba", action="store_true")
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--ahora", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--diagnostico", action="store_true")
    parser.add_argument("--paso-manual", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        return modo_dry_run()
    candado = tomar_candado_unico()
    if candado is None:
        print("❌ Ya hay otro bot de WhatsApp abierto en esta laptop: cierro este para no mandar todo duplicado.")
        return 3
    if args.diagnostico:
        return modo_diagnostico()
    if args.prueba:
        return modo_prueba(3 if args.limite is None else args.limite, args.paso_manual)
    return modo_programado(ahora=args.ahora)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Bot detenido.")
