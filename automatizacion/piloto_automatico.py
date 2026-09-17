import os
import re
import sys
import time
import random
import json
import subprocess
from playwright.sync_api import sync_playwright

# Fuerza UTF-8 en la salida: en Windows la consola suele usar cp1252, que no
# sabe representar los emojis de los prints de abajo y hace crashear el script.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

def _deshabilitar_quickedit_windows():
    # En Windows, un clic o una selección de texto en la ventana de la consola
    # activa "QuickEdit Mode" y pausa el proceso hasta que apretás Enter o Esc.
    # Como este script corre desatendido durante horas, eso lo deja "colgado"
    # sin ser un error real. Lo desactivamos al arrancar.
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
# Este script vive en automatizacion/, que está en .gitignore. Pero
# catalogo.js, indumentaria.js y Fotos/ tienen que quedar en la RAÍZ del
# repo (un nivel arriba), que es donde los lee index.html/minorista.html
# y donde SÍ los trackea git. Por eso subimos un nivel antes de arrancar,
# sin importar desde dónde ejecutes este archivo.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
print(f"[DEBUG] Este script está en: {os.path.abspath(__file__)}")
print(f"[DEBUG] REPO_ROOT calculado: {REPO_ROOT}")
print(f"[DEBUG] Carpeta de trabajo actual: {os.getcwd()}")
print(f"[DEBUG] ¿Existe .git acá?: {os.path.isdir(os.path.join(REPO_ROOT, '.git'))}")

# --- CONFIGURACIÓN ---
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
CARPETA_FOTOS = "Fotos"
ARCHIVO_JS = "catalogo.js"
ARCHIVO_INDUMENTARIA = "indumentaria.js"
ARCHIVO_ZAPATILLAS_MANUAL = "zapatillas_manual.js"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 5
TIMEOUT_PRODUCTO_MS = 15000

# Palabras clave para blindar el catálogo de zapatillas: si algún producto de
# la tienda online contiene alguna de estas palabras, se descarta siempre,
# aunque aparezca con stock. Así nunca se mezcla indumentaria en catalogo.js.
PALABRAS_INDUMENTARIA = ["remera", "baggy"]
# ---------------------

def limpiar_nombre_archivo(nombre):
    if not nombre:
        return ""
    nombre_limpio = nombre.replace("/", " ").replace("\\", " ").replace("\u00a0", " ")
    return " ".join(nombre_limpio.split())

def cargar_listado_completo(page):
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
                except:
                    pass

        actual = page.locator('.js-item-product, .product-container').count()

        if actual == anterior:
            estable += 1
            if estable >= ESTABLE_LIMITE:
                break
        else:
            estable = 0

        anterior = actual

def extraer_productos(page):
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

            # Blindaje: si el nombre del producto coincide con indumentaria,
            # se ignora siempre. Esta lista se maneja aparte, a mano, en
            # indumentaria.js y nunca debe mezclarse acá.
            nombre_lower = nombre.lower()
            if any(palabra in nombre_lower for palabra in PALABRAS_INDUMENTARIA):
                continue

            texto_tarjeta = tarjeta.inner_text().lower()
            if "sin stock" in texto_tarjeta or "agotado" in texto_tarjeta:
                continue

            vistos.add(href)
            productos.append((nombre, href))
        except:
            continue
    return productos

def talles_disponibles_en_producto(page, url):
    page.goto(url, wait_until="networkidle", timeout=TIMEOUT_PRODUCTO_MS)
    disponibles = {}

    try:
        variantes_json = page.evaluate("""() => {
            if (window.LS && window.LS.variants) {
                return JSON.stringify(window.LS.variants);
            }
            return null;
        }""")

        if variantes_json:
            variants = json.loads(variantes_json)
            for v in variants:
                stock_val = v.get('stock')
                cant = 0

                if isinstance(stock_val, int) and stock_val > 0:
                    cant = stock_val
                elif isinstance(stock_val, str) and stock_val.isdigit():
                    cant = int(stock_val)
                elif stock_val is True:
                    cant = 99

                if cant > 0:
                    for opt in ['option0', 'option1', 'option2']:
                        val = v.get(opt)
                        if val:
                            numeros = re.findall(r'\d+', str(val))
                            for num in numeros:
                                num_int = int(num)
                                if 15 <= num_int <= 50:
                                    disponibles[num_int] = max(disponibles.get(num_int, 0), cant)

            if disponibles:
                return [{"talle": k, "stock": v} for k, v in sorted(disponibles.items())]
    except Exception as e:
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
                        disponibles[num_int] = 99
    except:
        pass

    return [{"talle": k, "stock": v} for k, v in sorted(disponibles.items())]

def rutina_actualizacion():
    print("\n--- INICIANDO ESCANEO DE STOCK (ZAPATILLAS) ---")
    productos_finales = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Abriendo {URL_LISTADO} ...")
        page.goto(URL_LISTADO, wait_until="networkidle")
        try:
            page.locator("text=Entendido").first.click(timeout=3000)
        except:
            pass

        print("Cargando catálogo completo...")
        cargar_listado_completo(page)

        productos_detectados = extraer_productos(page)
        print(f"Modelos con posible stock detectados: {len(productos_detectados)}")

        for i, (nombre, url) in enumerate(productos_detectados, 1):
            try:
                talles_datos = talles_disponibles_en_producto(page, url)
                if not talles_datos:
                    continue

                nombre_archivo = limpiar_nombre_archivo(nombre)
                ruta_foto_final = ""
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    ruta_prueba = os.path.join(CARPETA_FOTOS, f"{nombre_archivo}{ext}")
                    if os.path.exists(ruta_prueba):
                        ruta_foto_final = f"Fotos/{nombre_archivo}{ext}"
                        break

                if ruta_foto_final:
                    productos_finales.append({
                        "modelo": nombre,
                        "talles": talles_datos,
                        "foto": ruta_foto_final
                    })
            except:
                continue

        browser.close()

    # Guarda únicamente las zapatillas como stock_zapatillas en catalogo.js
    with open(ARCHIVO_JS, "w", encoding="utf-8") as f:
        f.write("const stock_zapatillas = [\n")
        for p in productos_finales:
            talles_json = json.dumps(p['talles'])
            f.write(f"  {{ modelo: '{p['modelo']}', talles: {talles_json}, foto: '{p['foto']}' }},\n")
        f.write("];\n")

    # --- AUTOMATIZACIÓN DE GITHUB ---
    # Sube catalogo.js (zapatillas, generado acá) Y también indumentaria.js
    # (que vos editás a mano), para que ninguno de los dos quede desactualizado
    # en la web publicada.
    try:
        hora_subida = time.strftime('%H:%M:%S')
        subprocess.run(["git", "pull", "origin", "main"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        archivos_a_subir = [ARCHIVO_JS]
        if os.path.exists(ARCHIVO_INDUMENTARIA):
            archivos_a_subir.append(ARCHIVO_INDUMENTARIA)
        if os.path.exists(ARCHIVO_ZAPATILLAS_MANUAL):
            archivos_a_subir.append(ARCHIVO_ZAPATILLAS_MANUAL)
        if os.path.isdir(CARPETA_FOTOS):
            # Sube fotos nuevas o modificadas que hayas agregado a mano
            archivos_a_subir.append(CARPETA_FOTOS)

        subprocess.run(["git", "add"] + archivos_a_subir, check=True)

        resultado_commit = subprocess.run(["git", "commit", "-m", f"Stock actualizado (zapatillas + indumentaria) a las {hora_subida}"], capture_output=True, text=True)

        if "nothing to commit" not in resultado_commit.stdout:
            subprocess.run(["git", "push", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[{hora_subida}] 🔄 HUBO CAMBIOS: Se actualizó la web (zapatillas y/o indumentaria).")
        else:
            print(f"[{hora_subida}] ⏸️ NO HUBO CAMBIOS: El stock sigue igual.")

    except Exception as e:
        print(f"⚠️ Error al verificar o subir a GitHub: {e}")

def main():
    print("🤖 PILOTO AUTOMÁTICO DE ZAPATILLAS")
    while True:
        try:
            rutina_actualizacion()
        except Exception as e:
            print(f"\n❌ Hubo un error inesperado: {e}")

        minutos_espera = random.uniform(14, 18)
        print(f"\n[{time.strftime('%H:%M:%S')}] Durmiendo... Próximo escaneo en {minutos_espera:.1f} minutos.\n")
        time.sleep(int(minutos_espera * 60))

if __name__ == "__main__":
    main()
