import os
import re
import sys
import time
import random
import json
import subprocess # NUEVO: Para controlar Git automáticamente
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN ---
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
CARPETA_FOTOS = "Fotos"
ARCHIVO_JS = "catalogo.js"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 3
TIMEOUT_PRODUCTO_MS = 15000
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
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(700)
        boton = page.locator(".js-load-more")
        if boton.count() > 0:
            style = (boton.first.get_attribute("style") or "").replace(" ", "")
            if "display:none" not in style:
                try:
                    boton.first.click(timeout=2000)
                    page.wait_for_timeout(900)
                except:
                    pass
        actual = page.locator(".js-quickshop-modal-open").count()
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
    print("\n--- INICIANDO ESCANEO DE STOCK ---")
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
                    print(f"  [{i}/{len(productos_detectados)}] ✅ OK: {nombre} ({len(talles_datos)} talles)")
                else:
                    print(f"  [{i}/{len(productos_detectados)}] ⚠️ Sin foto local: {nombre}")
                    
            except Exception as e:
                print(f"  [{i}/{len(productos_detectados)}] ❌ Error al leer modelo: {nombre}")
                continue
                
        browser.close()

    # Guarda el archivo local
    with open(ARCHIVO_JS, "w", encoding="utf-8") as f:
        f.write("const stock_actualizado = [\n")
        for p in productos_finales:
            talles_json = json.dumps(p['talles'])
            f.write(f"  {{ modelo: '{p['modelo']}', talles: {talles_json}, foto: '{p['foto']}' }},\n")
        f.write("];\n")
    
    print(f"\n✅ Catálogo local actualizado. Guardando en la nube...")

    # --- NUEVA AUTOMATIZACIÓN DE GITHUB ---
    try:
        hora_subida = time.strftime('%H:%M:%S')
        # Ejecuta git add, commit y push silenciosamente
        subprocess.run(["git", "add", ARCHIVO_JS], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # El comando commit puede fallar si no hay cambios reales en el stock, lo manejamos suavemente
        resultado_commit = subprocess.run(["git", "commit", "-m", f"Stock actualizado a las {hora_subida}"], capture_output=True, text=True)
        
        if "nothing to commit" not in resultado_commit.stdout:
            subprocess.run(["git", "push", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"🚀 ¡ÉXITO! Stock subido a tu página pública.")
        else:
            print(f"📌 Sin cambios: El proveedor no modificó el stock desde el último escaneo.")
            
    except Exception as e:
        print(f"⚠️ Error al subir a GitHub: {e} (Se reintentará en el próximo ciclo)")
    # ----------------------------------------

def main():
    print("🤖 PILOTO AUTOMÁTICO VINCULADO A INTERNET")
    print("El sistema actualizará tu web pública periódicamente. Podés minimizar esta ventana.\n")
    
    while True:
        try:
            rutina_actualizacion()
        except Exception as e:
            print(f"\n❌ Hubo un error inesperado: {e}")
        
        minutos_espera = random.uniform(14, 18)
        print(f"\n[{time.strftime('%H:%M:%S')}] Misión cumplida. Durmiendo... Próximo escaneo en {minutos_espera:.1f} minutos.\n")
        time.sleep(int(minutos_espera * 60))

if __name__ == "__main__":
    main()