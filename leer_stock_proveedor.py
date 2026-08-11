import re
import sys

from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN --------------------------------------------------------
URL_LISTADO = "https://vestitepiola.mitiendanube.com/productos/?order=best-selling"
ARCHIVO_SALIDA = "stock_proveedor.txt"
MAX_SCROLLS = 200
ESTABLE_LIMITE = 3
TIMEOUT_PRODUCTO_MS = 15000
# ---------------------------------------------------------------------------


def cargar_listado_completo(page):
    """Hace scroll y clickea 'Mostrar más productos' cuando esté visible,
    hasta que la cantidad de productos deje de aumentar."""
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


def extraer_productos(html: str):
    """Devuelve, en orden de aparición, lista de (nombre, url) sin duplicados."""
    productos = []
    vistos = set()
    for m in re.finditer(
        r'<a\s+href="(https://[^"]*?/productos/[^"/?#]+/)"\s+title="([^"]+)"',
        html,
        re.IGNORECASE,
    ):
        href, nombre = m.group(1), m.group(2).strip()
        if href in vistos:
            continue
        vistos.add(href)
        productos.append((nombre, href))
    return productos


def talles_disponibles_en_producto(page, url: str):
    """Extrae el stock DIRECTAMENTE del sistema interno de Tiendanube."""
    page.goto(url, wait_until="networkidle", timeout=TIMEOUT_PRODUCTO_MS)
    disponibles = set()

    # ESTRATEGIA 1: Leer directamente la base de datos de variantes (LS.variants)
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

    # ESTRATEGIA 2 (De Respaldo): Si la primera falla, leemos los menús desplegables
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
    """
    Agrupa los talles usando comas (ej: 40, 41, 42). 
    Solo usa "X al Y" si hay 4 o más talles consecutivos (ej: 34 al 37).
    """
    if not talles:
        return None
        
    talles = sorted(list(set(talles)))
    resultado = []
    
    # Separar en grupos de números consecutivos
    grupos = []
    grupo_actual = [talles[0]]
    
    for t in talles[1:]:
        if t == grupo_actual[-1] + 1:
            grupo_actual.append(t)
        else:
            grupos.append(grupo_actual)
            grupo_actual = [t]
    grupos.append(grupo_actual)
    
    # Formatear la salida final
    for grupo in grupos:
        if len(grupo) >= 4:
            resultado.append(f"{grupo[0]} al {grupo[-1]}")
        else:
            for num in grupo:
                resultado.append(str(num))
                
    return ", ".join(resultado)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Abriendo {URL_LISTADO} ...")
        page.goto(URL_LISTADO, wait_until="networkidle")
        try:
            page.locator("text=Entendido").first.click(timeout=3000)
        except Exception:
            pass

        print("Cargando todo el catálogo (scroll)...")
        html_listado = cargar_listado_completo(page)

        productos = extraer_productos(html_listado)
        print(f"Modelos encontrados en el catálogo: {len(productos)}")

        if not productos:
            print("No se encontraron productos. Puede que la tienda haya cambiado su diseño.")
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
                print(f"  [{i}/{len(productos)}] {nombre}: error al leerlo ({type(e).__name__}), lo salteo")
                if fallas_seguidas >= MAX_FALLAS_SEGUIDAS:
                    print(
                        f"\nSe cortó: fallaron {MAX_FALLAS_SEGUIDAS} productos seguidos. "
                        "Algo cambió en la tienda o hay un problema de conexión. "
                        "No sigo para no perder más tiempo."
                    )
                    browser.close()
                    sys.exit(1)
                continue

            texto_talles = formatear_talles(talles)
            
            # Acá ignora por completo las zapatillas que no tienen ningún stock
            if texto_talles is None:
                print(f"  [{i}/{len(productos)}] {nombre}: SIN STOCK, se ignora")
                continue

            print(f"  [{i}/{len(productos)}] {nombre}: {texto_talles}")
            lineas.append(nombre)
            lineas.append(texto_talles)
            lineas.append("")
            incluidos += 1

        browser.close()

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas).strip() + "\n")

    print(f"\nListo. {len(productos)} modelos revisados, {incluidos} con stock real guardados en el txt.")
    print(f"Se generó {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()