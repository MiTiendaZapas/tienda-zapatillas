import os
import re
import sys
import time
import random
import json
from io import BytesIO
from PIL import Image
import win32clipboard
from playwright.sync_api import sync_playwright

# Fuerza UTF-8 en la salida: en Windows la consola suele usar cp1252, que no
# sabe representar los emojis de los prints de abajo y hace crashear el script.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def _deshabilitar_quickedit_windows():
    # En Windows, un clic o una selección de texto en la ventana de la consola
    # activa "QuickEdit Mode" y CONGELA el script hasta apretar Enter o Esc
    # (parece que "no avanza" aunque no haya ningún error). Al desactivarlo
    # ya no hay forma de congelarlo por accidente; el costo es que no se puede
    # seleccionar texto con el mouse en esta ventana, por eso todo lo que se
    # imprime queda también guardado en automatizacion/logs/bot_whatsapp.log.
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE = -10
        ENABLE_EXTENDED_FLAGS = 0x0080
        ENABLE_QUICK_EDIT_MODE = 0x0040
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        modo = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(modo)):
            nuevo_modo = (modo.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS
            kernel32.SetConsoleMode(handle, nuevo_modo)
    except Exception:
        pass

_deshabilitar_quickedit_windows()

# --- FIJA LA CARPETA DE TRABAJO A LA RAÍZ DEL REPO ---
# Este script vive en automatizacion/, que está en .gitignore. Pero Fotos/ y
# zapatillas_manual.js están un nivel arriba, en la raíz del repo. Por eso
# subimos un nivel antes de arrancar, sin importar desde dónde lo ejecutes.
# La sesión de WhatsApp (sesion_wsp/) queda guardada dentro de automatizacion/
# para no mezclarla con los archivos que sí sube git.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(REPO_ROOT)

# --- LOG A ARCHIVO ---
# Todo lo que se imprime en la consola se copia (con hora) a
# automatizacion/logs/bot_whatsapp.log, que está dentro de la carpeta ignorada
# por git. Así, si algo falla o se traba, se puede ver qué pasó y cuándo sin
# tener que copiar texto de la ventana.
import logging
from logging.handlers import RotatingFileHandler

def _configurar_log_a_archivo(nombre_archivo):
    carpeta = os.path.join(SCRIPT_DIR, "logs")
    os.makedirs(carpeta, exist_ok=True)
    handler = RotatingFileHandler(os.path.join(carpeta, nombre_archivo), maxBytes=5_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger = logging.getLogger(nombre_archivo)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

class _CopiarSalidaALog:
    def __init__(self, flujo, logger):
        self._flujo = flujo
        self._logger = logger
        self._pendiente = ""

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

# --- CONFIGURACIÓN GENERAL ---
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
ARCHIVO_SALIDA = "stock_proveedor.txt"
CARPETA_FOTOS = "Fotos"
RUTA_ZAPATILLAS_MANUAL = "zapatillas_manual.js"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 5
TIMEOUT_PRODUCTO_MS = 15000

# Mensaje de precios que se manda como texto (sin foto), UNA sola vez,
# después de haber mandado todas las fotos de zapatillas. Es texto fijo:
# si el día de mañana cambiás alguno de estos precios en tienda.js, hay
# que venir a actualizarlo acá también a mano.
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
# -----------------------------

def limpiar_nombre_archivo(nombre):
    """Limpia barras, caracteres invisibles y espacios múltiples para cazar la foto sí o sí"""
    if not nombre:
        return ""
    nombre_limpio = nombre.replace("/", " ").replace("\\", " ").replace("\u00a0", " ")
    return " ".join(nombre_limpio.split())

def _goto_con_reintentos(page, url, intentos=3, espera_seg=15, **kwargs):
    # Sin esto, un corte de internet justo al abrir la tienda o WhatsApp Web
    # (antes de que arranque el resto del manejo de errores del script)
    # tiraba una excepcion sin capturar y cortaba todo el bot de una.
    for intento in range(1, intentos + 1):
        try:
            return page.goto(url, **kwargs)
        except Exception as e:
            if intento == intentos:
                raise
            print(f"  ⚠️ No se pudo abrir {url} (intento {intento}/{intentos}): {e}")
            print(f"  Reintentando en {espera_seg}s...")
            time.sleep(espera_seg)

def copiar_imagen_al_portapapeles(ruta_imagen):
    imagen = Image.open(ruta_imagen)
    salida = BytesIO()
    imagen.convert("RGB").save(salida, "BMP")
    data = salida.getvalue()[14:] 
    salida.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

def enviar_mensaje_texto(page, texto):
    """
    Manda un mensaje de SOLO TEXTO (sin foto) al chat que ya está abierto
    en WhatsApp Web. Se usa para el mensaje final de precios, después de
    haber mandado todas las fotos de zapatillas.
    """
    barra_mensaje = page.locator('div[contenteditable="true"]').last
    barra_mensaje.click()
    page.wait_for_timeout(500)

    lineas_texto = texto.split('\n')
    for i, linea in enumerate(lineas_texto):
        page.keyboard.insert_text(linea)
        if i < len(lineas_texto) - 1:
            page.keyboard.press("Shift+Enter")

    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

def cargar_listado_completo(page):
    # Misma lógica que usa piloto_automatico.py. La versión anterior de este
    # bot esperaba muy poco entre scrolls (700ms, 3 vueltas iguales) y daba
    # el listado por terminado con ~220 de ~400 tarjetas. Hoy lo que quedaba
    # sin cargar era casi todo "sin stock", pero el orden del listado es por
    # más vendidos, no por stock, así que un modelo con stock podía quedar
    # afuera sin aviso.
    estable = 0
    anterior = -1

    for _ in range(MAX_SCROLLS):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        page.wait_for_timeout(1000)

        boton = page.locator(".js-load-more")
        if boton.count() > 0:
            style = (boton.first.get_attribute("style") or "").replace(" ", "")
            if "display:none" not in style:
                try:
                    page.evaluate("window.scrollBy(0, -150);")
                    boton.first.click(timeout=3000)
                    page.wait_for_timeout(2500)
                except Exception:
                    pass

        actual = page.locator('.js-item-product, .product-container').count()

        if actual == anterior:
            estable += 1
            if estable >= ESTABLE_LIMITE:
                break
        else:
            estable = 0

        anterior = actual

def extraer_productos_con_filtro(page):
    productos = []
    vistos = set()
    
    tarjetas = page.locator('.js-item-product').all()
    if not tarjetas:
        tarjetas = page.locator('article, .product-container').all()

    for tarjeta in tarjetas:
        try:
            link = tarjeta.locator('a[href*="/productos/"]').first
            if link.count() == 0:
                continue
            href = link.get_attribute("href")
            nombre = link.get_attribute("title") or link.inner_text().strip()
            
            if not href or not nombre or href in vistos:
                continue
                
            texto_tarjeta = tarjeta.inner_text().lower()
            if "sin stock" in texto_tarjeta or "agotado" in texto_tarjeta:
                continue
                
            vistos.add(href)
            productos.append((nombre, href))
        except Exception:
            continue
            
    return productos

def talles_disponibles_en_producto(page, url: str):
    # No se espera a "networkidle" (que esperaba a que carguen imágenes,
    # trackers y demás, ~2.4s por página, mucho más con wifi lento): los datos
    # de stock (window.LS.variants) ya están disponibles apenas se arma el
    # HTML. Medido contra la tienda real: ~0.5s por página con resultados
    # idénticos. Las páginas de producto se abren en una pestaña que además
    # bloquea imágenes/fuentes/estilos (ver actualizar_stock).
    page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_PRODUCTO_MS)
    disponibles = set()

    try:
        page.wait_for_function("window.LS && window.LS.variants", timeout=8000)
    except Exception:
        pass

    try:
        variants = page.evaluate("window.LS ? window.LS.variants : null")
        if variants:
            for v in variants:
                stock = v.get('stock')
                if isinstance(stock, str) and stock.isdigit():
                    stock = int(stock)
                if stock is True or (isinstance(stock, int) and stock > 0):
                    for opt in ['option0', 'option1', 'option2']:
                        val = v.get(opt)
                        if val:
                            numeros = re.findall(r'\d+', str(val))
                            for num in numeros:
                                num_int = int(num)
                                if 15 <= num_int <= 50:
                                    disponibles.add(num_int)
            if disponibles:
                return disponibles
    except Exception:
        pass

    try:
        opciones = page.locator('select option')
        if opciones.count() > 0:
            for i in range(opciones.count()):
                opcion = opciones.nth(i)
                texto = opcion.inner_text().strip().lower()
                
                if "sin stock" in texto or "agotado" in texto or opcion.get_attribute('disabled') is not None:
                    continue

                numeros = re.findall(r'\d+', texto)
                for num in numeros:
                    num_int = int(num)
                    if 15 <= num_int <= 50:
                        disponibles.add(num_int)
                        
            if disponibles:
                return disponibles
    except Exception:
        pass

    return disponibles

def formatear_talles(talles):
    if not talles:
        return None
        
    talles = sorted(list(set(talles)))
    resultado = []
    grupos = []
    grupo_actual = [talles[0]]
    
    for t in talles[1:]:
        if t == grupo_actual[-1] + 1:
            grupo_actual.append(t)
        else:
            grupos.append(grupo_actual)
            grupo_actual = [t]
    grupos.append(grupo_actual)
    
    for grupo in grupos:
        if len(grupo) >= 4:
            resultado.append(f"{grupo[0]} al {grupo[-1]}")
        else:
            for num in grupo:
                resultado.append(str(num))
                
    return ", ".join(resultado)

# Modelos de ojotas que no tienen la palabra "ojotas" en el nombre, pero se
# venden y se muestran igual que el resto de las ojotas (talles bi-numerales).
# Tiene que coincidir EXACTO (en minúsculas) con lo que ya usan tienda.js y
# minorista.js, para que el mensaje de WhatsApp diga lo mismo que la web.
MODELOS_OJOTAS_BINUMERAL = ["mind beige", "mind gris", "mind negras", "mind blancas"]

def es_modelo_ojota(nombre):
    n = nombre.lower().strip()
    return "ojotas" in n or n in MODELOS_OJOTAS_BINUMERAL

def formatear_talles_ojota(talles):
    """
    Junta los talles de a pares consecutivos (39, 40 -> "39/40"), igual que
    procesarTallesOjota() en tienda.js/minorista.js, para que el texto que se
    manda por WhatsApp coincida con cómo se ven los talles en la web.
    """
    if not talles:
        return None

    numeros = sorted(set(talles))
    resultado = []
    for i in range(0, len(numeros), 2):
        if i + 1 < len(numeros):
            resultado.append(f"{numeros[i]}/{numeros[i+1]}")
        else:
            resultado.append(str(numeros[i]))

    return ", ".join(resultado)

# Mismo patrón que usa el Panel Admin para leer zapatillas_manual.js: cada
# producto es { modelo: '...', talles: [{"talle": N, "stock": N}, ...], foto: '...' }
_PATRON_STOCK_MANUAL = re.compile(
    r"\{\s*modelo:\s*'((?:[^'\\]|\\.)*)'\s*,\s*talles:\s*(\[.*?\])\s*,\s*foto:\s*'((?:[^'\\]|\\.)*)'\s*\}",
    re.DOTALL,
)

def cargar_zapatillas_manual(ruta=RUTA_ZAPATILLAS_MANUAL):
    """
    Lee el stock que cargaste a mano (desde el Panel Admin o editando el
    archivo directo) en zapatillas_manual.js. Devuelve una lista de
    (nombre_modelo, set_de_talles) con SOLO los talles que tienen stock > 0
    (un talle cargado con stock 0 no se manda como disponible).
    """
    if not os.path.exists(ruta):
        return []

    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    productos = []
    for match in _PATRON_STOCK_MANUAL.finditer(contenido):
        nombre_crudo, talles_raw, _foto = match.groups()
        nombre = nombre_crudo.replace("\\'", "'")

        try:
            talles = json.loads(talles_raw)
        except json.JSONDecodeError:
            talles = []

        talles_disponibles = set()
        for t in talles:
            try:
                numero = int(t.get("talle"))
                stock = int(t.get("stock", 0))
            except (TypeError, ValueError):
                continue
            if stock > 0:
                talles_disponibles.add(numero)

        if talles_disponibles:
            productos.append((nombre, talles_disponibles))

    return productos

def fusionar_stock_tienda_y_casa(productos_manual, productos_proveedor):
    """
    Junta el stock manual (casa, zapatillas_manual.js) con el escaneado en
    vivo de la tienda del proveedor -- igual que hace mezclar_stock.js en la
    web: si el mismo modelo aparece en los dos lados, se combinan los
    talles en una sola entrada (no se manda dos veces el mismo modelo).

    Los modelos que están en zapatillas_manual.js van SIEMPRE primero en el
    resultado (estén o no también en la tienda), y recién después los que
    son solamente de la tienda del proveedor, en el orden en que se
    escanearon.

    La comparación de "es el mismo modelo" es por nombre exacto (sin
    importar mayúsculas/minúsculas ni espacios de más), igual que en el
    Panel Admin y en mezclar_stock.js -- para que se fusionen, el nombre
    tiene que estar escrito igual en los dos lados.
    """
    combinados = {}
    orden = []

    for nombre, talles in productos_manual:
        clave = nombre.lower().strip()
        combinados[clave] = {"nombre": nombre, "talles": set(talles)}
        orden.append(clave)

    for nombre, talles in productos_proveedor:
        clave = nombre.lower().strip()
        if clave in combinados:
            combinados[clave]["talles"] |= set(talles)
        else:
            combinados[clave] = {"nombre": nombre, "talles": set(talles)}
            orden.append(clave)

    return [(combinados[clave]["nombre"], combinados[clave]["talles"]) for clave in orden]

def foto_local_existe(nombre_archivo):
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        if os.path.exists(os.path.join(CARPETA_FOTOS, f"{nombre_archivo}{ext}")):
            return True
    return False

def _guardar_archivo_atomico(destino, contenido):
    # Se escribe primero en una carpeta temporal (ignorada por git) y recién
    # cuando está completo se mueve a Fotos/. Así el piloto, que hace "git add
    # Fotos" por su cuenta, nunca puede llegar a subir una foto a medio bajar.
    # El nombre temporal incluye el número de proceso: si el piloto y el bot
    # bajan la MISMA foto a la vez (por ejemplo los dos arrancan a las 8), no
    # pisan el mismo archivo temporal. Si al mover justo el otro proceso está
    # dejando ese mismo archivo, se reintenta; y si ya quedó ahí, está bien.
    carpeta_tmp = os.path.join(SCRIPT_DIR, "_descargas_tmp")
    os.makedirs(carpeta_tmp, exist_ok=True)
    tmp = os.path.join(carpeta_tmp, f"{os.path.basename(destino)}.{os.getpid()}.part")
    with open(tmp, "wb") as f:
        f.write(contenido)

    ultimo_error = None
    for _ in range(5):
        try:
            os.replace(tmp, destino)
            return
        except PermissionError as e:
            ultimo_error = e
            time.sleep(0.2)
    try:
        os.remove(tmp)
    except OSError:
        pass
    if not os.path.exists(destino):
        raise ultimo_error

def descargar_foto_producto(page, ruta_destino_sin_extension):
    # Se llama con "page" ya posicionada en la página del producto. Toma la
    # imagen principal (.js-product-slide-img) y, de su "srcset", la variante
    # de mayor resolución (normalmente 1024px) en vez del thumbnail chico.
    # Devuelve la ruta guardada, o "" si no pudo (en ese caso el modelo
    # simplemente queda sin foto, como antes).
    try:
        img = page.locator(".js-product-slide-img").first
        if img.count() == 0:
            return ""

        url_elegida = None
        mejor_ancho = -1
        for parte in (img.get_attribute("srcset") or "").split(","):
            trozos = parte.strip().rsplit(" ", 1)
            if len(trozos) != 2:
                continue
            try:
                ancho = int(trozos[1].rstrip("w"))
            except ValueError:
                continue
            if ancho > mejor_ancho:
                mejor_ancho = ancho
                url_elegida = trozos[0]

        if not url_elegida:
            url_elegida = img.get_attribute("src") or ""
        if not url_elegida:
            return ""
        if url_elegida.startswith("//"):
            url_elegida = "https:" + url_elegida

        respuesta = page.request.get(url_elegida, timeout=TIMEOUT_PRODUCTO_MS)
        if not respuesta.ok:
            return ""
        contenido = respuesta.body()

        # Se confirma que realmente sea una imagen antes de guardarla.
        Image.open(BytesIO(contenido)).verify()

        extension = os.path.splitext(url_elegida.split("?")[0])[1] or ".jpg"
        ruta_destino = f"{ruta_destino_sin_extension}{extension}"
        _guardar_archivo_atomico(ruta_destino, contenido)
        return ruta_destino
    except Exception:
        return ""

def actualizar_stock(p):
    # Recibe el "p" de Playwright ya abierto en vez de crear el suyo propio,
    # para poder correr esto varias veces (una por tanda) sin anidar
    # sync_playwright() adentro del que ya mantiene abierta la sesion de
    # WhatsApp. Devuelve True/False en vez de sys.exit(1): un escaneo fallido
    # no debe matar el proceso ni cerrar la sesion de WhatsApp ya abierta,
    # solo esa tanda.
    print("--- FASE 1: ESCANEANDO Y FILTRANDO STOCK EN TIENDANUBE ---")
    browser = p.chromium.launch(headless=True)
    try:
        page = browser.new_page()

        print(f"Abriendo {URL_LISTADO} ...")
        _goto_con_reintentos(page, URL_LISTADO, wait_until="networkidle")
        try:
            page.locator("text=Entendido").first.click(timeout=3000)
        except Exception:
            pass

        print("Cargando catálogo completo...")
        cargar_listado_completo(page)

        productos = extraer_productos_con_filtro(page)
        print(f"Modelos con potencial stock detectados en catálogo: {len(productos)}")

        if not productos:
            print("❌ No se encontraron productos.")
            return False

        # Pestaña aparte para las páginas de producto: no necesitan imágenes,
        # fuentes ni estilos para leer el stock, y bloquearlos las hace ~5
        # veces más rápidas. (El listado de arriba sí se carga completo tal
        # cual, porque su scroll infinito depende de cómo se ve la página.)
        page_producto = browser.new_page()
        page_producto.route(
            "**/*",
            lambda ruta: ruta.abort() if ruta.request.resource_type in ("image", "font", "media", "stylesheet") else ruta.continue_(),
        )

        productos_proveedor = []
        fallas_seguidas = 0
        MAX_FALLAS_SEGUIDAS = 4
        fotos_descargadas = 0

        for i, (nombre, url) in enumerate(productos, start=1):
            talles = None
            for intento in (1, 2):
                try:
                    talles = talles_disponibles_en_producto(page_producto, url)
                    break
                except Exception as e:
                    if intento == 1:
                        # Un fallo puntual (por ejemplo un corte de wifi de
                        # unos segundos) no tiene que contar como falla.
                        time.sleep(5)

            if talles is None:
                fallas_seguidas += 1
                print(f"  [{i}/{len(productos)}] {nombre}: error al leerlo, saltando...")
                if fallas_seguidas >= MAX_FALLAS_SEGUIDAS:
                    print("\nSe cortó: fallaron demasiados productos seguidos.")
                    return False
                continue
            fallas_seguidas = 0

            if not talles:
                continue

            print(f"  [{i}/{len(productos)}] {nombre}: {len(talles)} talles escaneados")
            productos_proveedor.append((nombre, talles))

            nombre_archivo = limpiar_nombre_archivo(nombre)
            if not foto_local_existe(nombre_archivo):
                ruta_foto = descargar_foto_producto(page_producto, os.path.join(CARPETA_FOTOS, nombre_archivo))
                if ruta_foto:
                    fotos_descargadas += 1
                    print(f"    📷 Foto nueva descargada: {ruta_foto.replace(os.sep, '/')}")

        if fotos_descargadas:
            print(f"\n📷 Se descargaron {fotos_descargadas} foto(s) nueva(s) a Fotos/ (el piloto las sube a GitHub en su próximo ciclo).")
    finally:
        browser.close()

    # --- Sumamos el stock de casa (zapatillas_manual.js) con el escaneado ---
    productos_manual = cargar_zapatillas_manual()
    if productos_manual:
        print(f"\n📦 Stock manual (casa) cargado: {len(productos_manual)} modelo(s) desde {RUTA_ZAPATILLAS_MANUAL}")

    productos_finales = fusionar_stock_tienda_y_casa(productos_manual, productos_proveedor)

    lineas = []
    incluidos = 0
    for nombre, talles in productos_finales:
        texto_talles = formatear_talles_ojota(talles) if es_modelo_ojota(nombre) else formatear_talles(talles)
        if texto_talles is None:
            continue
        lineas.append(nombre)
        lineas.append(texto_talles)
        lineas.append("")
        incluidos += 1

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas).strip() + "\n")

    print(f"\n✅ Análisis finalizado. {incluidos} modelos con stock real guardados en {ARCHIVO_SALIDA} (stock de casa primero)\n")
    return True

def parsear_stock_txt():
    items = []
    if not os.path.exists(ARCHIVO_SALIDA):
        return items
        
    with open(ARCHIVO_SALIDA, "r", encoding="utf-8") as f:
        lineas = f.read().strip().split('\n')
        
    for i in range(0, len(lineas), 3):
        if i + 1 < len(lineas):
            modelo = lineas[i].strip()
            talles = lineas[i+1].strip()
            if modelo and talles:
                items.append({"modelo": modelo, "texto": f"{modelo}\n{talles}"})
    return items

def obtener_items_con_foto(p):
    if not actualizar_stock(p):
        return []

    items = parsear_stock_txt()
    if not items:
        print("❌ No hay items para enviar en el archivo de stock.")
        return []

    print("Revisando fotos disponibles en la carpeta...")
    items_con_foto = []
    extensiones = ['.jpg', '.jpeg', '.png', '.webp']

    for item in items:
        modelo_original = item["modelo"]
        modelo_archivo = limpiar_nombre_archivo(modelo_original)

        foto_encontrada = None
        for ext in extensiones:
            ruta_prueba = os.path.join(CARPETA_FOTOS, f"{modelo_archivo}{ext}")
            if os.path.exists(ruta_prueba):
                foto_encontrada = ruta_prueba
                break

        if foto_encontrada:
            item["ruta_foto"] = foto_encontrada
            items_con_foto.append(item)
        else:
            print(f"⚠️ Sin foto para: '{modelo_original}' (buscado como '{modelo_archivo}').")

    if not items_con_foto:
        print("\n❌ No hay fotos disponibles para enviar.")

    return items_con_foto

def enviar_item(page, item):
    modelo = item["modelo"]
    texto = item["texto"]
    foto_a_subir = item["ruta_foto"]

    try:
        print(f"Preparando foto de: {modelo}...")

        copiar_imagen_al_portapapeles(foto_a_subir)

        barra_mensaje = page.locator('div[contenteditable="true"]').last
        barra_mensaje.click()
        page.wait_for_timeout(500)

        page.keyboard.press("Control+V")
        page.wait_for_timeout(3500)

        lineas_texto = texto.split('\n')
        for i, linea in enumerate(lineas_texto):
            page.keyboard.insert_text(linea)
            if i < len(lineas_texto) - 1:
                page.keyboard.press("Shift+Enter")

        page.wait_for_timeout(1000)

        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

        # TIEMPO DE ESPERA AJUSTADO: Entre 5 y 20 segundos
        espera = random.uniform(5, 15)
        print(f"✅ Enviado: {modelo}. Esperando {espera:.1f} segundos...")
        time.sleep(espera)
        return True

    except Exception as e:
        print(f"❌ Error al enviar {modelo}: {e}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        page.keyboard.press("Escape")
        return False

def main():
    # A diferencia de antes (una corrida = un envío y listo), esto ahora
    # queda "prendido" como el piloto_automatico: abre WhatsApp Web UNA sola
    # vez, hace el paso manual UNA sola vez (para destrabar el bloqueo de
    # WhatsApp), y de ahí en más cada ENTER escanea el stock de nuevo y
    # manda una tanda entera 100% automática, sin cerrar ni reabrir nada.
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=os.path.join(SCRIPT_DIR, "sesion_wsp"),
            headless=False
        )
        page = browser.new_page()

        print("Abriendo WhatsApp Web...")
        _goto_con_reintentos(page, "https://web.whatsapp.com/")

        primera_tanda = True

        while True:
            if not primera_tanda:
                print("\n" + "=" * 65)
                input("👉 Apretá ENTER para escanear el stock y mandar una tanda nueva (o cerrá esta ventana para salir): ")

            print("\n--- FASE 1: ESCANEANDO STOCK ---")
            items_con_foto = obtener_items_con_foto(p)
            if not items_con_foto:
                print("No hay nada para enviar en esta tanda.")
                primera_tanda = False
                continue

            print("\n--- FASE 2: ENVIANDO POR WHATSAPP ---")
            if primera_tanda:
                primer_item = items_con_foto[0]
                items_a_enviar = items_con_foto[1:]

                print("\n" + "=" * 65)
                print("🛑 PASO MANUAL, SOLO ESTA PRIMERA VEZ (DESTROZANDO EL BLOQUEO DE WHATSAPP) 🛑")
                print("1. Entrá a tu grupo de WhatsApp en la ventana que se abrió.")
                print(f"2. Buscá y adjuntá a mano la primera foto: {primer_item['modelo']}")
                print("3. Ponele este texto:")
                print("-" * 30)
                print(primer_item['texto'])
                print("-" * 30)
                input("👉 Cuando la foto esté ENVIADA, apretá ENTER acá: ")
                print("=" * 65 + "\n")
                enviados = 1
                primera_tanda = False
            else:
                items_a_enviar = items_con_foto
                enviados = 0

            print("¡Iniciando el envío automático!...")
            page.wait_for_timeout(3000)

            for item in items_a_enviar:
                if enviar_item(page, item):
                    enviados += 1

            print("\nMandando el mensaje final de precios...")
            try:
                page.wait_for_timeout(1500)
                enviar_mensaje_texto(page, MENSAJE_FINAL_PRECIOS)
                print("✅ Mensaje final de precios enviado.")
            except Exception as e:
                print(f"❌ Error al mandar el mensaje final de precios: {e}")

            print(f"\n¡Tanda terminada! Se enviaron {enviados} fotos con éxito.")

if __name__ == "__main__":
    main()