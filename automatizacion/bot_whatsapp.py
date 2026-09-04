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

# --- CONFIGURACIÓN GENERAL ---
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
ARCHIVO_SALIDA = "stock_proveedor.txt"
CARPETA_FOTOS = "Fotos"
RUTA_ZAPATILLAS_MANUAL = "zapatillas_manual.js"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 3
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
    estable = 0
    anterior = -1
    for _ in range(MAX_SCROLLS):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(700)

        boton = page.locator(".js-load-more")
        if boton.count() > 0:
            style = (boton.first.get_attribute("style") or "").replace(" ", "")
            if "display:none" not in style:
                try:
                    boton.first.click(timeout=2000)
                    page.wait_for_timeout(900)
                except Exception:
                    pass

        actual = page.locator(".js-quickshop-modal-open").count()
        if actual == anterior:
            estable += 1
            if estable >= ESTABLE_LIMITE:
                break
        else:
            estable = 0
        anterior = actual

    return page.content()

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
    page.goto(url, wait_until="networkidle", timeout=TIMEOUT_PRODUCTO_MS)
    disponibles = set()

    try:
        variants = page.evaluate("window.LS ? window.LS.variants : null")
        if variants:
            for v in variants:
                stock = v.get('stock')
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

def actualizar_stock():
    print("--- FASE 1: ESCANEANDO Y FILTRANDO STOCK EN TIENDANUBE ---")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Abriendo {URL_LISTADO} ...")
        page.goto(URL_LISTADO, wait_until="networkidle")
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
            browser.close()
            sys.exit(1)

        productos_proveedor = []
        fallas_seguidas = 0
        MAX_FALLAS_SEGUIDAS = 4

        for i, (nombre, url) in enumerate(productos, start=1):
            try:
                talles = talles_disponibles_en_producto(page, url)
                fallas_seguidas = 0
            except Exception as e:
                fallas_seguidas += 1
                print(f"  [{i}/{len(productos)}] {nombre}: error al leerlo, saltando...")
                if fallas_seguidas >= MAX_FALLAS_SEGUIDAS:
                    print("\nSe cortó: fallaron demasiados productos seguidos.")
                    browser.close()
                    sys.exit(1)
                continue

            if not talles:
                continue

            print(f"  [{i}/{len(productos)}] {nombre}: {len(talles)} talles escaneados")
            productos_proveedor.append((nombre, talles))

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

def main():
    actualizar_stock()

    items = parsear_stock_txt()
    if not items:
        print("❌ No hay items para enviar en el archivo de stock.")
        return

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
        return

    primer_item = items_con_foto[0]
    resto_items = items_con_foto[1:]

    print("\n--- FASE 2: ENVIANDO POR WHATSAPP ---")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./sesion_wsp",
            headless=False 
        )
        page = browser.new_page()
        
        print("Abriendo WhatsApp Web...")
        page.goto("https://web.whatsapp.com/")
        
        print("\n" + "="*65)
        print("🛑 PASO MANUAL (DESTROZANDO EL BLOQUEO DE WHATSAPP) 🛑")
        print("1. Entrá a tu grupo de WhatsApp en la ventana que se abrió.")
        print(f"2. Buscá y adjuntá a mano la primera foto: {primer_item['modelo']}")
        print("3. Ponele este texto:")
        print("-" * 30)
        print(primer_item['texto'])
        print("-" * 30)
        input("👉 Cuando la foto esté ENVIADA, apretá ENTER acá: ")
        print("="*65 + "\n")

        print("¡Iniciando el envío masivo automático!...")
        page.wait_for_timeout(3000) 
        
        enviados = 1 

        for item in resto_items:
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
                
                enviados += 1
                
                # TIEMPO DE ESPERA AJUSTADO: Entre 5 y 20 segundos
                espera = random.uniform(5, 15)
                print(f"✅ Enviado: {modelo}. Esperando {espera:.1f} segundos...")
                time.sleep(espera)
                
            except Exception as e:
                print(f"❌ Error al enviar {modelo}: {e}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                page.keyboard.press("Escape")

        print("\nMandando el mensaje final de precios...")
        try:
            page.wait_for_timeout(1500)
            enviar_mensaje_texto(page, MENSAJE_FINAL_PRECIOS)
            print("✅ Mensaje final de precios enviado.")
        except Exception as e:
            print(f"❌ Error al mandar el mensaje final de precios: {e}")

        print(f"\n¡Terminado! Se actualizaron los datos y se enviaron {enviados} fotos con éxito.")
        
        try:
            browser.close()
        except:
            pass

if __name__ == "__main__":
    main()