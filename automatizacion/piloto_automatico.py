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

# --- LOG A ARCHIVO ---
# Todo lo que se imprime en la consola se copia (con fecha y hora) a
# automatizacion/logs/piloto_automatico.log, dentro de la carpeta ignorada por
# git. Sirve para ver qué pasó cuando algo falla mientras nadie mira la ventana.
import logging
from logging.handlers import RotatingFileHandler

def _configurar_log_a_archivo(nombre_archivo):
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
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
    _logger_piloto = _configurar_log_a_archivo("piloto_automatico.log")
    sys.stdout = _CopiarSalidaALog(sys.stdout, _logger_piloto)
    sys.stderr = _CopiarSalidaALog(sys.stderr, _logger_piloto)
except Exception:
    pass

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

# Espera normal entre escaneos (minutos). El escaneo en sí suma 5-7 min más
# aparte de esta espera, así que el ciclo completo ronda los 15-20 min.
ESPERA_MIN_MINUTOS = 10
ESPERA_MAX_MINUTOS = 14
# Si un escaneo no detecta NINGÚN producto (posible caída o bloqueo del
# sitio), se espera este tiempo fijo antes de reintentar, en vez del ciclo
# normal, para no insistir de golpe contra un sitio que puede estar caído.
ESPERA_SIN_PRODUCTOS_MINUTOS = 30

# Horario de descanso: de 00:00 a 07:30 no escanea ni molesta al sitio del
# proveedor, aunque la laptop siga prendida (de noche no hay nadie atendiendo
# pedidos). Termina a las 7:30 para que el primer ciclo del día (unos 7 min)
# ya haya bajado y subido las fotos nuevas cuando se prende el bot de
# WhatsApp a las 8. Con INICIO=00:00 el rango nunca cruza la medianoche, lo
# que simplifica la cuenta de cuánto falta para que termine.
INICIO_DESCANSO = (0, 0)   # (hora, minuto)
FIN_DESCANSO = (7, 30)

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

def descargar_foto_producto(page, ruta_destino_sin_extension):
    # Se llama con "page" ya posicionada en la página del producto (la deja
    # ahí talles_disponibles_en_producto). Busca la imagen principal
    # (.js-product-slide-img, la primera con src real) y de su "srcset" saca
    # la variante de mayor resolución disponible (normalmente 1024x1024) en
    # vez de quedarse con el thumbnail chico que trae el "src" por defecto.
    try:
        img = page.locator(".js-product-slide-img").first
        if img.count() == 0:
            return ""

        url_elegida = None
        srcset = img.get_attribute("srcset") or ""
        mejor_ancho = -1
        for parte in srcset.split(","):
            parte = parte.strip()
            if not parte:
                continue
            trozos = parte.rsplit(" ", 1)
            if len(trozos) != 2:
                continue
            url_candidata, ancho_str = trozos
            try:
                ancho = int(ancho_str.rstrip("w"))
            except ValueError:
                continue
            if ancho > mejor_ancho:
                mejor_ancho = ancho
                url_elegida = url_candidata

        if not url_elegida:
            url_elegida = img.get_attribute("src") or ""
        if not url_elegida:
            return ""
        if url_elegida.startswith("//"):
            url_elegida = "https:" + url_elegida

        extension = os.path.splitext(url_elegida.split("?")[0])[1] or ".jpg"
        ruta_destino = f"{ruta_destino_sin_extension}{extension}"

        respuesta = page.request.get(url_elegida, timeout=TIMEOUT_PRODUCTO_MS)
        if not respuesta.ok:
            return ""

        # Se escribe primero en una carpeta temporal (ignorada por git) y
        # recién completo se mueve a Fotos/: el bot de WhatsApp también puede
        # bajar fotos ahí, y este script hace "git add Fotos", así que nunca
        # debe quedar una foto a medio escribir a la vista.
        # El nombre temporal incluye el número de proceso porque el bot puede
        # estar bajando la MISMA foto al mismo tiempo (por ej. si los dos
        # arrancan a las 8). Si al mover el otro proceso está dejando ese
        # mismo archivo se reintenta, y si ya quedó ahí está bien.
        carpeta_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_descargas_tmp")
        os.makedirs(carpeta_tmp, exist_ok=True)
        ruta_tmp = os.path.join(carpeta_tmp, f"{os.path.basename(ruta_destino)}.{os.getpid()}.part")
        with open(ruta_tmp, "wb") as f:
            f.write(respuesta.body())

        ultimo_error = None
        for _ in range(5):
            try:
                os.replace(ruta_tmp, ruta_destino)
                return ruta_destino
            except PermissionError as e:
                ultimo_error = e
                time.sleep(0.2)
        try:
            os.remove(ruta_tmp)
        except OSError:
            pass
        if not os.path.exists(ruta_destino):
            raise ultimo_error

        return ruta_destino
    except Exception:
        return ""

def en_horario_de_descanso(ahora=None):
    ahora = ahora or time.localtime()
    minuto_del_dia = ahora.tm_hour * 60 + ahora.tm_min
    return INICIO_DESCANSO[0] * 60 + INICIO_DESCANSO[1] <= minuto_del_dia < FIN_DESCANSO[0] * 60 + FIN_DESCANSO[1]

def segundos_hasta_fin_de_descanso(ahora=None):
    # Solo se llama estando ya dentro del horario de descanso (que empieza
    # a medianoche), así que nunca hay que cruzar a otro día.
    ahora = ahora or time.localtime()
    segundos_desde_medianoche = ahora.tm_hour * 3600 + ahora.tm_min * 60 + ahora.tm_sec
    return max(FIN_DESCANSO[0] * 3600 + FIN_DESCANSO[1] * 60 - segundos_desde_medianoche, 0)

def _sincronizar_y_subir(intentos=3, espera_seg=15):
    # pull + push se reintentan JUNTOS como una unidad: si el push falla
    # porque justo alguien más subió algo (la tienda nueva se trabaja en
    # paralelo y también hace push al mismo repo), reintentar solo el push
    # fallaría igual las 3 veces; hay que volver a traer lo nuevo primero.
    # También cubre un corte breve de wifi. Se muestra el motivo REAL que da
    # git (antes se descartaba y no había forma de saber por qué falló).
    for intento in range(1, intentos + 1):
        for paso, comando in (("git pull", ["git", "pull", "origin", "main", "--no-edit"]),
                              ("git push", ["git", "push", "origin", "main"])):
            resultado = subprocess.run(comando, capture_output=True, text=True)
            if resultado.returncode != 0:
                motivo = (resultado.stderr or resultado.stdout or "sin mensaje").strip()
                print(f"  ⚠️ Falló {paso} (intento {intento}/{intentos}): {motivo}")
                if intento == intentos:
                    raise RuntimeError(f"{paso} falló {intentos} veces seguidas: {motivo}")
                time.sleep(espera_seg)
                break
        else:
            return

def _limpiar_merge_colgado():
    # A veces git termina de crear el commit del merge pero no llega a borrar
    # .git/MERGE_HEAD (en Windows, por ejemplo, si otro programa tiene el
    # archivo abierto justo en ese momento). Mientras exista, TODOS los
    # "git pull" siguientes fallan con "You have not concluded your merge" y
    # el piloto no puede volver a subir nada hasta que alguien lo limpie a
    # mano. Solo se limpia si el merge ya quedó commiteado (MERGE_HEAD ya es
    # parte del historial de HEAD) y no hay conflictos sin resolver; un merge
    # realmente a medias no se toca.
    ruta_merge_head = os.path.join(".git", "MERGE_HEAD")
    if not os.path.exists(ruta_merge_head):
        return
    if subprocess.run(["git", "ls-files", "-u"], capture_output=True, text=True).stdout.strip():
        return
    with open(ruta_merge_head, encoding="utf-8") as f:
        sha = f.read().strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"]).returncode == 0:
        subprocess.run(["git", "merge", "--quit"])
        print("🧹 Se limpió un merge que había quedado colgado (ya estaba commiteado); si no, bloqueaba todos los pull.")

def _commits_sin_subir():
    # Cuántos commits locales todavía no llegaron a GitHub (por ejemplo si un
    # push anterior falló). Es una consulta local, no usa la red.
    resultado = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"], capture_output=True, text=True)
    try:
        return int(resultado.stdout.strip())
    except ValueError:
        return 0

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

                if not ruta_foto_final:
                    ruta_descargada = descargar_foto_producto(page, os.path.join(CARPETA_FOTOS, nombre_archivo))
                    if ruta_descargada:
                        ruta_foto_final = ruta_descargada.replace(os.sep, "/")
                        print(f"  📷 Foto nueva descargada para '{nombre}': {ruta_foto_final}")

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
    #
    # Orden importante: primero committeamos el escaneo local y RECIÉN
    # DESPUÉS hacemos pull. Si se hiciera al revés (pull con catalogo.js
    # modificado y sin commitear todavía), un choque con otra máquina que
    # haya pusheado en el medio (por ej. si alguna vez queda prendido el
    # piloto en otra PC a la vez) puede mezclar el pull con cambios sueltos
    # de forma más frágil. Pulleando sobre un working tree limpio, un
    # conflicto real en catalogo.js lo resuelve solo el merge driver "ours"
    # configurado en .gitattributes (se queda con la versión local, que es
    # siempre la más fresca porque se regenera de cero en cada escaneo) en
    # vez de dejar marcas de conflicto pegadas en el archivo que lee la web.
    try:
        hora_subida = time.strftime('%H:%M:%S')

        archivos_a_subir = [ARCHIVO_JS]
        if os.path.exists(ARCHIVO_INDUMENTARIA):
            archivos_a_subir.append(ARCHIVO_INDUMENTARIA)
        if os.path.exists(ARCHIVO_ZAPATILLAS_MANUAL):
            archivos_a_subir.append(ARCHIVO_ZAPATILLAS_MANUAL)
        if os.path.isdir(CARPETA_FOTOS):
            # Sube fotos nuevas o modificadas que hayas agregado a mano
            archivos_a_subir.append(CARPETA_FOTOS)

        _limpiar_merge_colgado()

        subprocess.run(["git", "add"] + archivos_a_subir, check=True)

        resultado_commit = subprocess.run(["git", "commit", "-m", f"Stock actualizado (zapatillas + indumentaria) a las {hora_subida}"], capture_output=True, text=True)

        hay_commit_nuevo = "nothing to commit" not in resultado_commit.stdout
        pendientes = _commits_sin_subir()

        if hay_commit_nuevo or pendientes > 0:
            # Si un push anterior falló, los commits quedan solo en esta
            # laptop: hay que seguir intentando subirlos aunque este ciclo no
            # haya cambiado nada, si no la web queda desactualizada.
            _sincronizar_y_subir()
            if hay_commit_nuevo:
                print(f"[{hora_subida}] 🔄 HUBO CAMBIOS: Se actualizó la web (zapatillas y/o indumentaria).")
            else:
                print(f"[{hora_subida}] 🔄 Se subieron {pendientes} commit(s) que habían quedado pendientes de un intento anterior.")
        else:
            print(f"[{hora_subida}] ⏸️ NO HUBO CAMBIOS: El stock sigue igual.")

    except Exception as e:
        print(f"⚠️ Error al verificar o subir a GitHub: {e}")

    return len(productos_detectados)

def main():
    print("🤖 PILOTO AUTOMÁTICO DE ZAPATILLAS")
    mejor_conteo_visto = 0
    while True:
        if en_horario_de_descanso():
            segundos = segundos_hasta_fin_de_descanso()
            print(f"\n😴 [{time.strftime('%H:%M:%S')}] Horario de descanso ({INICIO_DESCANSO[0]:02d}:{INICIO_DESCANSO[1]:02d}-{FIN_DESCANSO[0]:02d}:{FIN_DESCANSO[1]:02d}). Durmiendo {segundos / 3600:.1f} h hasta las {FIN_DESCANSO[0]:02d}:{FIN_DESCANSO[1]:02d}...\n")
            time.sleep(segundos)
            continue

        total_productos = 0
        try:
            total_productos = rutina_actualizacion()
        except Exception as e:
            print(f"\n❌ Hubo un error inesperado: {e}")

        if total_productos == 0:
            # Nada detectado: puede ser un corte del sitio o un bloqueo. En
            # vez de reintentar enseguida con el ciclo normal, se espera el
            # tiempo fijo largo para no insistir contra un sitio caído.
            minutos_espera = ESPERA_SIN_PRODUCTOS_MINUTOS
            print(f"⚠️ No se detectó ningún producto en la tienda (¿corte o bloqueo del sitio?). Espera extendida antes de reintentar.")
        elif mejor_conteo_visto > 0 and total_productos < mejor_conteo_visto / 2:
            # Se detectó bastante menos de lo normal: se estira la espera
            # dentro del ciclo normal, más cuanto más lejos esté de lo usual.
            proporcion_faltante = 1 - (total_productos / mejor_conteo_visto)
            extra_minutos = (ESPERA_SIN_PRODUCTOS_MINUTOS - ESPERA_MAX_MINUTOS) * proporcion_faltante
            minutos_espera = random.uniform(ESPERA_MIN_MINUTOS, ESPERA_MAX_MINUTOS) + extra_minutos
            print(f"⚠️ Se detectaron {total_productos} productos, menos de la mitad de los {mejor_conteo_visto} vistos normalmente. Se extiende la espera por las dudas.")
        else:
            # El escaneo en sí (recorrer todos los productos) suma en
            # promedio 5-7 min más aparte de esta espera. Este rango apunta a
            # que el ciclo completo (escaneo + espera) quede entre 15 y 20
            # minutos.
            minutos_espera = random.uniform(ESPERA_MIN_MINUTOS, ESPERA_MAX_MINUTOS)

        if total_productos > mejor_conteo_visto:
            mejor_conteo_visto = total_productos

        print(f"\n[{time.strftime('%H:%M:%S')}] Durmiendo... Próximo escaneo en {minutos_espera:.1f} minutos.\n")
        time.sleep(int(minutos_espera * 60))

if __name__ == "__main__":
    main()
