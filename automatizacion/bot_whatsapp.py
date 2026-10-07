"""Bot de WhatsApp: manda el stock del catálogo a un grupo, todos los días a una hora al azar.

Lee el catálogo que ya mantiene el piloto (catalogo/productos.json de
mitiendazapas.github.io): no scrapea al proveedor.

Modos:
    python bot_whatsapp.py                    programado: cada día a una hora al azar (HORA_DESDE..HORA_HASTA)
    python bot_whatsapp.py --prueba           manda 3 modelos + el mensaje de precios al GRUPO DE PRUEBA
    python bot_whatsapp.py --prueba --limite 10
    python bot_whatsapp.py --prueba-programador   prueba larga del programa completo (todo el catálogo, hora sorteada en 1-3 min) al GRUPO DE PRUEBA
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

# Los nombres de los grupos de ESTA laptop se guardan en bot_config.json (junto a este archivo, fuera de
# git): {"grupo_real": "...", "grupo_prueba": "..."}. Si existe, pisa los valores de arriba.
CONFIG_LOCAL = SCRIPT_DIR / "bot_config.json"
try:
    _config = json.loads(CONFIG_LOCAL.read_text(encoding="utf-8"))
    GRUPO_REAL = _config.get("grupo_real", GRUPO_REAL)
    GRUPO_PRUEBA = _config.get("grupo_prueba", GRUPO_PRUEBA)
except FileNotFoundError:
    pass
except Exception as _error:
    print(f"⚠️ No pude leer {CONFIG_LOCAL.name}: {_error}")

HORA_DESDE = (7, 45)              # cada día se sortea una hora entre estas dos
HORA_HASTA = (8, 10)
ESPERA_TRAS_CARGAR_SEG = 90       # pausa tras cargar la lista de chats, antes del primer envío
DIAS_SIN_ENVIO = (6,)            # días en que NO se manda stock (0 = lunes ... 6 = domingo)
TOLERANCIA_TARDE_MIN = 120        # si la laptop estaba apagada a esa hora, se manda igual hasta 2 h después
MAX_INTENTOS_DIA = 3
ESPERA_ENTRE_INTENTOS_MIN = 15
LIMITE_CARGA_MIN = 20             # tiempo máximo que se espera a que WhatsApp Web termine de sincronizar
ESPERA_CATALOGO_FRESCO_MIN = 30   # el piloto arranca a las 7:30: se espera a que publique su primera vuelta
CATALOGO_FRESCO_DESDE = (7, 30)

URL_CATALOGO = "https://mitiendazapas.github.io/catalogo/productos.json"
URL_CATALOGO_G5 = "https://mitiendazapas.github.io/catalogo/productos-g5.json"
URL_BASE_CATALOGO = "https://mitiendazapas.github.io/catalogo/"
CATALOGO_LOCAL = REPO_ROOT.parent / "mitiendazapas.github.io" / "catalogo"   # copia que mantiene el piloto en esta laptop
CACHE_FOTOS = SCRIPT_DIR / "_cache_fotos"
ARCHIVO_ESTADO = SCRIPT_DIR / "estado_bot.json"
PAUSA_ENTRE_ENVIOS = (5, 15)      # segundos, al azar
PAUSA_ANTES_SEPARADOR_G5 = (20, 35)   # más larga que entre fotos, para que el separador quede aparte
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

# Primer mensaje del día, antes de las fotos.
SALUDO_INICIAL = (
    "Buen día gente\n"
    "Les dejo el stock de hoy 👇👇👇"
)

# Zapatillas calidad G5 (otro proveedor): van aparte de las BR, después de un separador bien visible.
SEPARADOR_G5 = (
    "━━━━━━━━━━━━━━\n"
    "⬇️ ZAPATILLAS CALIDAD G5 ⬇️\n"
    "(talles europeos)\n"
    "━━━━━━━━━━━━━━"
)
MENSAJE_PRECIOS_G5 = (
    "Zapas g5\n"
    "💰Adulto $83.000c/u💰\n"
    "\n"
    "🚨 A partir de 5 las de adulto $78.000c/u🚨"
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


def cargar_productos_g5():
    """Productos G5 listos para mandar. Si el archivo no existe o falla, devuelve [] (se manda solo BR):
    las G5 nunca deben cortar ni demorar la tanda de siempre."""
    try:
        try:
            datos = json.loads(_descargar(f"{URL_CATALOGO_G5}?t={int(time.time())}", reintentos=2).decode("utf-8"))
            origen = "web"
        except Exception as error:
            local = CATALOGO_LOCAL / "productos-g5.json"
            if not local.exists():
                print(f"ℹ️ No hay catálogo G5 ({error}): se manda solo lo de BR.")
                return []
            print(f"⚠️ Catálogo G5 de la web no disponible ({error}); uso la copia local.")
            datos = json.loads(local.read_text(encoding="utf-8"))
            origen = "copia local"
        if not datos.get("products"):
            print("ℹ️ El catálogo G5 está vacío: se manda solo lo de BR.")
            return []
        productos = armar_productos(datos, g5=True)
        edad = _edad_catalogo(datos)
        print(f"⭐ Catálogo G5 de {origen} ({datos['generatedAt']}, hace {str(edad).split('.')[0]}): "
              f"{len(productos)} modelos G5 para mandar.")
        return productos
    except Exception as error:
        print(f"⚠️ No pude preparar las G5 ({type(error).__name__}: {error}): se manda solo lo de BR.")
        return []


def armar_productos(catalogo, g5=False):
    """Lista de {id, name, texto, foto} en el orden del catálogo (stock de casa primero).
    Con g5=True el texto lleva arriba la calidad y los talles se aclaran como europeos."""
    productos, sin_foto = [], []
    for producto in catalogo["products"]:
        talles = formatear_talles(producto["sizes"])
        if talles is None:
            continue
        if not producto.get("images"):
            sin_foto.append(producto["name"])
            continue
        texto = (f"⭐ CALIDAD G5\n{producto['name']}\nTalles europeos: {talles}" if g5
                 else f"{producto['name']}\n{talles}")
        productos.append({
            "id": producto["id"], "name": producto["name"],
            "texto": texto, "foto": producto["images"][0]["lg"],
        })
    if sin_foto:
        print(f"⚠️ {len(sin_foto)} modelo(s) con stock pero SIN foto en el catálogo, no se mandan: {', '.join(sin_foto)}")
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


def _linea_clave(texto):
    """Línea con la que se reconoce un mensaje ya enviado: la primera con letras o números, salteando el
    encabezado '⭐ CALIDAD G5' (igual en todas las G5) y los renglones de pura decoración (━━━)."""
    for linea in texto.split("\n"):
        if linea.lstrip().startswith("⭐"):
            continue
        clave = _solo_alfanumerico(linea)
        if clave:
            return clave
    return _solo_alfanumerico(texto)


def _clave_chat(texto):
    """Nombre de un chat para compararlo: solo letras y números. Los emojis del nombre aparecen en la
    lista de chats pero no en el título del chat abierto (WhatsApp los dibuja como imágenes), así que
    comparar con ellos hacía fallar la verificación. Si el nombre es solo emojis, se usa tal cual."""
    return _solo_alfanumerico(texto) or _norm(texto)


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
        # Con la lista ya visible WhatsApp sigue sincronizando un rato y va lento: los primeros envíos
        # tardaban en aparecer y se reintentaban (foto repetida). Se le da tiempo a asentarse.
        print(f"⏳ Dejo que WhatsApp termine de sincronizar ({ESPERA_TRAS_CARGAR_SEG}s)...")
        page.wait_for_timeout(ESPERA_TRAS_CARGAR_SEG * 1000)
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
        return _clave_chat(titulo)
    except Exception:
        return None


def abrir_grupo(page, nombre):
    """Abre el grupo buscándolo por nombre y comprueba que el chat abierto sea ESE grupo."""
    objetivo = _clave_chat(nombre)
    if _chat_abierto(page) == objetivo:
        return
    page.keyboard.press("Control+Alt+/")                 # atajo de WhatsApp Web: foco en el buscador
    page.wait_for_timeout(600)
    page.keyboard.press("Control+A")                     # el buscador conserva la búsqueda anterior: se borra antes de escribir
    page.keyboard.press("Backspace")
    page.wait_for_timeout(300)
    page.keyboard.insert_text(" ".join(re.sub(r"[^\w\s]", " ", nombre).split()) or nombre)   # se busca sin emojis

    # La búsqueda muestra primero una fila "Cargando…" y los resultados llegan después, a veces más
    # tarde de lo que parece. Se espera hasta que dejen de cargar y el resultado esté estable; recién
    # ahí se decide si el grupo existe y si es único. La lista puede reacomodarse justo antes del
    # clic, así que si falla se vuelve a leer y se reintenta.
    selector = page.locator("#pane-side span[title]")
    for intento in range(1, 4):
        inicio, estables, indices = time.time(), 0, []
        while time.time() - inicio < 20:
            titulos = selector.evaluate_all("elementos => elementos.map(e => e.getAttribute('title'))")
            cargando = any(_clave_chat(t) == "cargando" for t in titulos)
            indices = [i for i, t in enumerate(titulos) if _clave_chat(t) == objetivo]
            estables = estables + 1 if (not cargando and (indices or time.time() - inicio > 4)) else 0
            if estables >= 2:
                break
            page.wait_for_timeout(500)
        if not indices:
            page.keyboard.press("Escape")
            raise GrupoNoEncontrado(f"No encontré ningún chat llamado exactamente «{nombre}».")
        if len(indices) > 1:
            page.keyboard.press("Escape")
            raise GrupoNoEncontrado(f"Hay {len(indices)} chats llamados «{nombre}»: no sé a cuál mandar, no mando nada.")
        try:
            selector.nth(indices[0]).click(timeout=4000)
            break
        except PlaywrightTimeout:
            if intento == 3:
                raise GrupoNoEncontrado(f"Encontré «{nombre}» pero no pude abrirlo (la lista cambiaba).")
            page.wait_for_timeout(1000)
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


def _ultima_fila_enviada(page):
    """True si el último mensaje del chat ya no está 'Pendiente' (WhatsApp lo marca Enviado/Entregado/Leído)."""
    try:
        etiquetas = page.locator("#main [data-id]").last.evaluate(
            "fila => [...fila.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label') || '')",
            timeout=1500)
    except Exception:
        return False
    return any(x.strip() in ("Enviado", "Entregado", "Leído") for x in etiquetas)


def esperar_envio_nuevo(page, id_anterior, texto_esperado, timeout_seg=40):
    """True cuando aparece una fila nueva al final del chat con el texto que mandamos Y WhatsApp ya la
    marca como enviada (antes pasa por 'Pendiente': si se cierra el navegador en ese momento se pierde)."""
    # Se comparan solo letras y números: WhatsApp dibuja los emojis como imágenes y no
    # aparecen en el texto leído de la página (el mensaje salía bien pero no se reconocía).
    esperado = _linea_clave(texto_esperado)
    fin = time.time() + timeout_seg
    while time.time() < fin:
        id_actual, texto = _ultima_fila(page)
        if (id_actual and id_actual != id_anterior and esperado in _solo_alfanumerico(texto)
                and _ultima_fila_enviada(page)):
            return True
        page.wait_for_timeout(500)
    return False


def esperar_envios_pendientes(page, timeout_seg=120):
    """Antes de cerrar el navegador, espera a que ningún mensaje del chat siga 'Pendiente'."""
    fin = time.time() + timeout_seg
    while time.time() < fin:
        if page.locator('#main [aria-label="Pendiente"], #main [aria-label=" Pendiente "]').count() == 0:
            return True
        page.wait_for_timeout(1000)
    print("⚠️ Quedaron mensajes todavía 'enviándose' al cerrar.")
    return False


def _escribir_y_enviar(page, texto, seguir=None):
    """Escribe el texto y aprieta Enter. Si se pasa `seguir`, se consulta justo antes del Enter y,
    si devuelve False, NO se envía (devuelve False)."""
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        page.keyboard.insert_text(linea)
        if i < len(lineas) - 1:
            page.keyboard.press("Shift+Enter")
    page.wait_for_timeout(1000)
    if seguir is not None and not seguir():
        return False
    page.keyboard.press("Enter")
    return True


_JS_FILAS_NUEVAS = """(idBase) => {
    const filas = [...document.querySelectorAll('#main [data-id]')];
    const desde = filas.findIndex(f => f.dataset.id === idBase);
    return filas.slice(desde + 1).map(f => ({
        txt: f.innerText || '',
        etiquetas: [...f.querySelectorAll('[aria-label]')].map(x => (x.getAttribute('aria-label') || '').trim())
    }));
}"""


def _envios_nuevos(page, id_base, texto):
    """(mensajes con ese texto que hay DESPUÉS del último mensaje que había antes de mandar, cuántos de
    ellos ya figuran Enviado). Sin id_base no se puede saber: (0, 0)."""
    if not id_base:
        return 0, 0
    try:
        filas = page.evaluate(_JS_FILAS_NUEVAS, id_base)
    except Exception:
        return 0, 0
    esperado = _linea_clave(texto)
    coinciden = [f for f in filas if esperado in _solo_alfanumerico(f["txt"])]
    enviados = [f for f in coinciden if any(e in ("Enviado", "Entregado", "Leído") for e in f["etiquetas"])]
    return len(coinciden), len(enviados)


def _cerrar_vista_previa(page):
    """Si quedó abierta la vista previa de una foto (sin enviar), la descarta. Escape solo no alcanza:
    WhatsApp pregunta '¿Quieres descartar la selección?' y hay que apretar Descartar."""
    for _ in range(3):
        if page.locator('[aria-label="Añadir archivo"]').count() == 0:
            return
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
        boton = page.get_by_text("Descartar", exact=True)
        if boton.count():
            boton.first.click()
            page.wait_for_timeout(800)


def _esperar_rastro_del_envio(page, texto, id_base, sin_rastro_seg=60, previa_seg=60, total_seg=180):
    """Tras un envío sin confirmar, espera MUCHO antes de darlo por perdido (WhatsApp, recién cargado, puede
    tardar más de un minuto en mostrar un mensaje que sí sale: reintentar antes duplica la foto).
    True = el mensaje salió o sigue saliendo (NO reintentar); False = sin rastro, se puede reintentar."""
    inicio = time.time()
    sin_rastro = None
    while time.time() - inicio < total_seg:
        total, enviados = _envios_nuevos(page, id_base, texto)
        if enviados:
            return True
        if total:                                  # está, pero todavía 'Pendiente': esperar
            sin_rastro = None
        elif page.locator('[aria-label="Añadir archivo"]').count():
            sin_rastro = None                      # la vista previa sigue abierta: el Enter no se registró
            if time.time() - inicio > previa_seg:
                break
        else:
            sin_rastro = sin_rastro or time.time()
            if time.time() - sin_rastro > sin_rastro_seg:
                break
        page.wait_for_timeout(1000)
    if _envios_nuevos(page, id_base, texto)[0]:
        print("  ⚠️ El mensaje sigue 'Pendiente': no lo reintento para no duplicarlo.")
        return True
    return False


def _limpiar_antes_de_reintentar(page, texto, id_base):
    """Tras un envío sin confirmar: True si en realidad salió (no se repite); si no, cierra la vista
    previa y vacía la caja para que el reintento arranque limpio."""
    if _esperar_rastro_del_envio(page, texto, id_base):
        return True
    _cerrar_vista_previa(page)
    try:
        page.locator('div[contenteditable="true"]').last.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
    except Exception:
        pass
    page.wait_for_timeout(500)
    return False


def enviar_foto_con_texto(page, producto, id_base=None):
    """id_base: id del último mensaje del chat ANTES de empezar con este modelo (se mantiene igual entre
    el intento 1 y el 2, para saber si algo de este modelo ya salió)."""
    foto = obtener_foto(producto["foto"])
    copiar_imagen_al_portapapeles(foto)
    _cerrar_vista_previa(page)              # una vista previa colgada taparía la caja de texto
    if id_base is None:
        id_base, _ = _ultima_fila(page)
    caja = page.locator('div[contenteditable="true"]').last
    caja.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+V")
    page.wait_for_timeout(3500)
    page.keyboard.press("Control+A")        # por si quedó texto de un intento anterior: no duplicarlo
    page.keyboard.press("Delete")
    # Última barrera contra duplicados: si justo ahora ya apareció este modelo (salió tarde), no mandarlo otra vez.
    if not _escribir_y_enviar(page, producto["texto"], lambda: _envios_nuevos(page, id_base, producto["texto"])[0] == 0):
        print(f"  ⚠️ {producto['name']} ya había salido: no lo mando de nuevo.")
        _cerrar_vista_previa(page)
    return esperar_envio_nuevo(page, id_base, producto["texto"])


def enviar_texto(page, texto, id_base=None):
    if id_base is None:
        id_base, _ = _ultima_fila(page)
    page.locator('div[contenteditable="true"]').last.click()
    page.wait_for_timeout(500)
    if not _escribir_y_enviar(page, texto, lambda: _envios_nuevos(page, id_base, texto)[0] == 0):
        print("  ⚠️ El mensaje ya había salido: no lo mando de nuevo.")
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
    return esperar_envio_nuevo(page, id_base, texto)


def enviar_tanda(p, grupo, productos, estado=None, guardar=None, paso_manual=False, productos_g5=None):
    """Manda, en este orden: fotos BR, precios BR, separador G5, fotos G5, precios G5 (lo que falte, si hay
    estado). Los problemas con las G5 nunca cortan lo ya mandado de BR. Devuelve un resumen."""
    productos_g5 = productos_g5 or []
    ya = set(estado["enviados"]) if estado else set()
    pendientes = [x for x in productos if x["id"] not in ya]
    pendientes_g5 = [x for x in productos_g5 if x["id"] not in ya]
    marcas = estado if estado is not None else {}   # sin estado (modo prueba) las marcas viven solo en esta tanda
    cuenta = {"enviados": 0, "fallidos": 0, "seguidas": 0}
    g5_cortado = False
    print(f"📨 Grupo «{grupo}»: {len(pendientes)} por mandar ({len(ya)} ya enviados antes)"
          + (f", más {len(pendientes_g5)} G5." if productos_g5 else "."))

    contexto, page = abrir_whatsapp(p)
    try:
        abrir_grupo(page, grupo)

        def enviar_lista(lista, g5=False):
            """False solo si, en G5, fallaron 3 seguidas y se dejó de intentar (en BR eso corta todo)."""
            for numero, producto in enumerate(lista, 1):
                abrir_grupo(page, grupo)                       # vuelve a comprobar que sea el grupo correcto
                if paso_manual and cuenta["enviados"] == 0 and not ya:
                    print(f"\n🛑 PASO MANUAL: mandá a mano la foto de «{producto['name']}» con este texto:\n{producto['texto']}")
                    input("👉 Cuando esté ENVIADA, apretá ENTER acá: ")
                    ok = True
                else:
                    ok = False
                    id_base, _ = _ultima_fila(page)     # el mismo para los dos intentos de este modelo
                    for intento in (1, 2):
                        try:
                            ok = enviar_foto_con_texto(page, producto, id_base)
                        except Exception as error:
                            print(f"  ⚠️ {producto['name']} (intento {intento}): {error}")
                        if ok:
                            break
                        if intento == 1:
                            print(f"  ⚠️ {producto['name']}: el intento 1 no se confirmó, espero y reviso antes de reintentar.")
                            ok = _limpiar_antes_de_reintentar(page, producto["texto"], id_base)
                            if ok:
                                break
                    if ok:
                        repetidos = _envios_nuevos(page, id_base, producto["texto"])[0]
                        if repetidos > 1:
                            avisar("Bot de WhatsApp: mensaje repetido",
                                   f"«{producto['name']}» salió {repetidos} veces en el grupo. Borrá la repetida a mano.")
                etiqueta = "G5 " if g5 else ""
                if ok:
                    cuenta["enviados"] += 1
                    cuenta["seguidas"] = 0
                    if estado is not None:
                        estado["enviados"].append(producto["id"])
                        guardar()
                    pausa = random.uniform(*PAUSA_ENTRE_ENVIOS)
                    print(f"✅ [{etiqueta}{numero}/{len(lista)}] {producto['name']}. Pausa de {pausa:.0f}s...")
                    time.sleep(pausa)
                else:
                    cuenta["fallidos"] += 1
                    cuenta["seguidas"] += 1
                    print(f"❌ [{etiqueta}{numero}/{len(lista)}] {producto['name']}: no salió.")
                    if g5:
                        if cuenta["seguidas"] >= 3:
                            avisar("Bot de WhatsApp", "Fallaron 3 fotos G5 seguidas: dejo las G5 (lo de BR ya salió).")
                            return False
                        continue
                    if cuenta["enviados"] == 0 and cuenta["seguidas"] >= 2:
                        raise EnvioBloqueado("WhatsApp no aceptó el primer envío automático. "
                                             "Puede hacer falta el paso manual (--paso-manual).")
                    if cuenta["seguidas"] >= 3:
                        raise EnvioBloqueado("Fallaron 3 envíos seguidos: se corta para no seguir a ciegas.")
            return True

        def enviar_mensaje(marca, texto, nombre):
            """Manda un texto suelto una sola vez por día (la marca queda en el estado)."""
            if marcas.get(marca):
                return True
            abrir_grupo(page, grupo)
            print(f"Mandando {nombre}...")
            id_base, _ = _ultima_fila(page)
            ok = False
            for intento in (1, 2):
                try:
                    ok = enviar_texto(page, texto, id_base)
                except Exception as error:
                    print(f"  ⚠️ {nombre} (intento {intento}): {error}")
                    page.keyboard.press("Escape")
                if not ok and intento == 1:
                    # Antes de reintentar, esperar bien por si el primero salió tarde (no duplicar).
                    ok = _esperar_rastro_del_envio(page, texto, id_base)
                if ok:
                    break
            if ok:
                marcas[marca] = True
                if estado is not None:
                    guardar()
                print(f"✅ {nombre[0].upper() + nombre[1:]}: enviado.")
            else:
                print(f"❌ {nombre[0].upper() + nombre[1:]}: no salió.")
            return ok

        if pendientes and not marcas.get("saludo_enviado"):
            if enviar_mensaje("saludo_enviado", SALUDO_INICIAL, "el saludo inicial"):
                time.sleep(random.uniform(*PAUSA_ENTRE_ENVIOS))
        enviar_lista(pendientes)
        precios = enviar_mensaje("precios_enviados", MENSAJE_FINAL_PRECIOS, "el mensaje final de precios BR")

        precios_g5 = None
        if productos_g5:
            try:
                if not marcas.get("separador_g5_enviado"):
                    pausa = random.uniform(*PAUSA_ANTES_SEPARADOR_G5)
                    print(f"Pausa de {pausa:.0f}s antes del separador G5...")
                    time.sleep(pausa)
                    enviar_mensaje("separador_g5_enviado", SEPARADOR_G5, "el separador G5")
                g5_cortado = not enviar_lista(pendientes_g5, g5=True)
                if not g5_cortado:
                    precios_g5 = enviar_mensaje("precios_g5_enviados", MENSAJE_PRECIOS_G5, "el mensaje de precios G5")
                else:
                    precios_g5 = False
            except EnvioBloqueado as error:
                avisar("Bot de WhatsApp", f"Las G5 no se pudieron mandar: {error}")
                precios_g5 = False
        esperar_envios_pendientes(page)
    finally:
        contexto.close()
    return {"enviados": cuenta["enviados"], "fallidos": cuenta["fallidos"], "precios": precios,
            "precios_g5": precios_g5}


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
        # La hora de hoy ya pudo sortearse (y anunciarse) al terminar el último envío.
        proxima = estado.get("proxima") or {}
        hora = proxima["hora"] if proxima.get("dia") == hoy else sortear_hora()
        estado = {"dia": hoy, "hora": hora, "enviados": [], "precios_enviados": False,
                  "saludo_enviado": False, "separador_g5_enviado": False, "precios_g5_enviados": False,
                  "terminado": False, "intentos": 0, "resultado": None}
        if proxima.get("dia", "") > hoy:
            estado["proxima"] = proxima         # lo ya anunciado para un día futuro (ej. el lunes) se conserva
        h, m, s = map(int, estado["hora"].split(":"))
        limite = datetime.now().replace(hour=h, minute=m, second=s, microsecond=0) + timedelta(minutes=TOLERANCIA_TARDE_MIN)
        if not forzar_ahora and datetime.now().weekday() in DIAS_SIN_ENVIO:
            estado["terminado"] = True
            estado["resultado"] = "Hoy no se envía stock (domingo)."
            print(f"📅 Hoy ({hoy}) no se envía stock.")
        elif not forzar_ahora and datetime.now() > limite:
            # El bot se abrió después de la hora de hoy (por ejemplo de noche): no es un error ni
            # hace falta avisar, simplemente el primer envío es mañana.
            estado["terminado"] = True
            estado["resultado"] = "El bot arrancó después de la hora de hoy: el primer envío es mañana."
            print(f"📅 Hoy ({hoy}) ya pasó la hora de envío: el primer envío es mañana.")
        else:
            print(f"📅 Hoy ({hoy}) el bot manda a las {estado['hora']}.")
    if forzar_ahora and not estado["terminado"]:
        estado["hora"] = datetime.now().strftime("%H:%M:%S")
    guardar_estado(estado)
    return estado


def proximo_dia_de_envio(desde=None):
    """Primer día después de `desde` (hoy por defecto) en que se manda stock; salta los DIAS_SIN_ENVIO."""
    dia = (desde or datetime.now().date()) + timedelta(days=1)
    while dia.weekday() in DIAS_SIN_ENVIO:
        dia += timedelta(days=1)
    return dia


def anunciar_proximo_envio(estado):
    """Sortea (una sola vez) la hora del próximo día de envío, la guarda para que sea la que se use, y la muestra."""
    dia = proximo_dia_de_envio()
    proxima = estado.get("proxima") or {}
    if proxima.get("dia") != dia.isoformat():
        proxima = {"dia": dia.isoformat(), "hora": sortear_hora()}
        estado["proxima"] = proxima
        guardar_estado(estado)
    nombre = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")[dia.weekday()]
    cuando = "mañana" if dia == datetime.now().date() + timedelta(days=1) else "el"
    print(f"📅 PRÓXIMO ENVÍO: {cuando} {nombre} {dia.strftime('%d/%m')} a las {proxima['hora']} "
          f"(el bot lo hace solo; dejá esta ventana abierta).")


def ejecutar_envio_real(estado):
    """Un intento de envío al grupo real. Actualiza el estado según resultado."""
    estado["intentos"] += 1
    guardar_estado(estado)
    try:
        catalogo, origen = esperar_catalogo_fresco()
        productos = armar_productos(catalogo)
        print(f"📚 Catálogo de {origen} ({catalogo['generatedAt']}): {len(productos)} modelos para mandar.")
        productos_g5 = cargar_productos_g5()
        with sync_playwright() as p:
            resumen = enviar_tanda(p, GRUPO_REAL, productos, estado, lambda: guardar_estado(estado),
                                   productos_g5=productos_g5)
        estado["terminado"] = True
        estado["resultado"] = f"OK: {resumen['enviados']} enviados, {resumen['fallidos']} fallidos, precios={resumen['precios']}"
        if resumen["precios_g5"] is not None:
            estado["resultado"] += f", precios G5={resumen['precios_g5']}"
        if resumen["fallidos"]:
            avisar("Bot de WhatsApp", f"Terminó, pero {resumen['fallidos']} modelo(s) no salieron. Revisá el log.")
        if not resumen["precios"]:
            avisar("Bot de WhatsApp", "El mensaje final de precios NO salió: mandalo a mano en el grupo.")
        if resumen["precios_g5"] is False:
            avisar("Bot de WhatsApp", "El mensaje de precios G5 NO salió: revisá el grupo y mandalo a mano si falta.")
        print(f"🏁 {estado['resultado']}")
        anunciar_proximo_envio(estado)
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


_anunciado = []     # para repetir el aviso del próximo envío solo al arrancar el bot


def ciclo_diario():
    ahora = datetime.now()
    estado = estado_de_hoy()
    if estado["terminado"]:
        if estado.get("proxima", {}).get("dia") != proximo_dia_de_envio().isoformat() or not _anunciado:
            _anunciado.append(True)
            anunciar_proximo_envio(estado)
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


def modo_prueba_programador():
    """Prueba larga del programa COMPLETO (hora sorteada, espera, catálogo del día, envío de todo el
    catálogo, estado y reintentos) pero comprimida: la hora se sortea entre 1 y 3 minutos desde ahora.
    Usa su propio archivo de estado y SIEMPRE manda al grupo de prueba, así que no toca el envío real
    de mañana ni hay nada que revertir después."""
    global ARCHIVO_ESTADO, GRUPO_REAL, HORA_DESDE, HORA_HASTA, DIAS_SIN_ENVIO
    DIAS_SIN_ENVIO = ()        # la prueba corre cualquier día
    ahora = datetime.now()
    desde, hasta = ahora + timedelta(minutes=1), ahora + timedelta(minutes=3)
    HORA_DESDE, HORA_HASTA = (desde.hour, desde.minute), (hasta.hour, hasta.minute)
    ARCHIVO_ESTADO = SCRIPT_DIR / "estado_bot_prueba.json"
    ARCHIVO_ESTADO.unlink(missing_ok=True)
    GRUPO_REAL = GRUPO_PRUEBA
    print(f"🧪 PRUEBA DEL PROGRAMADOR: manda TODO el catálogo a «{GRUPO_PRUEBA}» entre las "
          f"{desde:%H:%M} y las {hasta:%H:%M}. No toca el envío real.")
    while True:
        ciclo_diario()
        estado = cargar_estado()
        if estado.get("terminado"):
            print(f"🏁 Prueba del programador terminada: {estado.get('resultado')}")
            return 0 if str(estado.get("resultado", "")).startswith("OK") else 1


def modo_prueba(limite, paso_manual):
    catalogo, origen = cargar_catalogo()
    productos = armar_productos(catalogo)
    productos_g5 = cargar_productos_g5()
    if limite:
        productos, productos_g5 = productos[:limite], productos_g5[:limite]
    print(f"🧪 PRUEBA en «{GRUPO_PRUEBA}»: {len(productos)} modelos BR + {len(productos_g5)} G5 "
          f"(catálogo de {origen}, {catalogo['generatedAt']}).")
    with sync_playwright() as p:
        resumen = enviar_tanda(p, GRUPO_PRUEBA, productos, paso_manual=paso_manual, productos_g5=productos_g5)
    print(f"🏁 Prueba terminada: {resumen}")
    return 0 if not resumen["fallidos"] and resumen["precios"] and resumen["precios_g5"] is not False else 1


def modo_dry_run():
    catalogo, origen = cargar_catalogo()
    productos = armar_productos(catalogo)
    print(f"Catálogo de {origen} ({catalogo['generatedAt']}, hace {_edad_catalogo(catalogo)}): "
          f"{len(catalogo['products'])} productos, {len(productos)} para mandar.")
    productos_g5 = cargar_productos_g5()
    print("=" * 40)
    print(f"ORDEN DE LA TANDA: 0) saludo  1) {len(productos)} fotos BR  2) precios BR  "
          + (f"3) separador G5  4) {len(productos_g5)} fotos G5  5) precios G5" if productos_g5 else "(sin G5 hoy)"))
    print("=" * 40)
    print("[0] SALUDO INICIAL:\n" + SALUDO_INICIAL)
    print("-" * 40)
    print("[1] FOTOS BR (las 3 primeras):")
    for producto in productos[:3]:
        print(producto["texto"])
        print("foto:", obtener_foto(producto["foto"]))
        print("-" * 40)
    if len(productos) > 3:
        print(f"... ({len(productos) - 3} modelos BR más)")
    print("[2] MENSAJE DE PRECIOS BR:\n" + MENSAJE_FINAL_PRECIOS)
    if productos_g5:
        print("-" * 40)
        print("[3] SEPARADOR (se manda con una pausa más larga antes):\n" + SEPARADOR_G5)
        print("-" * 40)
        print("[4] FOTOS G5 (las 3 primeras):")
        for producto in productos_g5[:3]:
            print(producto["texto"])
            print("foto:", obtener_foto(producto["foto"]))
            print("-" * 40)
        if len(productos_g5) > 3:
            print(f"... ({len(productos_g5) - 3} modelos G5 más)")
        print("[5] MENSAJE DE PRECIOS G5:\n" + MENSAJE_PRECIOS_G5)
    print("-" * 40)
    print(f"Grupo de prueba: «{GRUPO_PRUEBA}» | grupo real: {GRUPO_REAL!r} | "
          f"ventana diaria {HORA_DESDE[0]:02d}:{HORA_DESDE[1]:02d}-{HORA_HASTA[0]:02d}:{HORA_HASTA[1]:02d}")
    return 0


def modo_diagnostico():
    """Abre WhatsApp y comprueba que cada grupo configurado se encuentre y se abra bien. NO manda nada."""
    with sync_playwright() as p:
        contexto, page = abrir_whatsapp(p)
        try:
            print("✅ WhatsApp Web cargó la lista de chats (la sesión está vinculada).")
            for etiqueta, grupo in (("de prueba", GRUPO_PRUEBA), ("real", GRUPO_REAL)):
                if not grupo:
                    print(f"— Grupo {etiqueta}: sin configurar.")
                    continue
                abrir_grupo(page, grupo)
                print(f"✅ Grupo {etiqueta} «{grupo}»: encontrado una sola vez, abierto y verificado por el título.")
        finally:
            contexto.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prueba", action="store_true")
    parser.add_argument("--prueba-programador", action="store_true")
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
    if args.prueba_programador:
        return modo_prueba_programador()
    if args.prueba:
        return modo_prueba(3 if args.limite is None else args.limite, args.paso_manual)
    return modo_programado(ahora=args.ahora)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Bot detenido.")
