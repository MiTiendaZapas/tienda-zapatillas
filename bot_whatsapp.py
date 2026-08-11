import os
import re
import sys
import time
import random
from io import BytesIO
from PIL import Image
import win32clipboard
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN GENERAL ---
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
ARCHIVO_SALIDA = "stock_proveedor.txt"
CARPETA_FOTOS = "Fotos"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 3
TIMEOUT_PRODUCTO_MS = 15000
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

        lineas = []
        incluidos = 0
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

            texto_talles = formatear_talles(talles)
            if texto_talles is None:
                continue

            print(f"  [{i}/{len(productos)}] {nombre}: {texto_talles}")
            lineas.append(nombre)
            lineas.append(texto_talles)
            lineas.append("")
            incluidos += 1

        browser.close()

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas).strip() + "\n")

    print(f"\n✅ Análisis finalizado. {incluidos} modelos con stock real guardados en {ARCHIVO_SALIDA}\n")

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

        print(f"\n¡Terminado! Se actualizaron los datos y se enviaron {enviados} fotos con éxito.")
        
        try:
            browser.close()
        except:
            pass

if __name__ == "__main__":
    main()