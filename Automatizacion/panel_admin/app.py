"""
Panel Admin - TiendaZapasOficial
=================================
App web local (Flask) para agilizar el trabajo diario de la tienda:
  - Ver qué productos escaneados del proveedor (catalogo.js) todavía no
    tienen foto cargada en Fotos/, y subirla directo desde el navegador.
  - Agregar / editar / borrar modelos de stock manual (zapatillas_manual.js
    e indumentaria.js) con un formulario, sin tocar código.
  - Prender y apagar piloto_automatico.py y bot_whatsapp.py con un botón,
    viendo su salida en vivo, sin pasar por la terminal.
  - Publicar los cambios a GitHub cuando vos decidas (botón manual).

Corre 100% local. No expone nada a internet: solo escucha en 127.0.0.1.
"""

import os
import re
import sys
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory, render_template

# ------------------------------------------------------------------
# Ubicación de archivos: la app se puede colocar en cualquier
# subcarpeta del repo (ej. automatizacion/panel_admin/) y de todos
# modos encuentra la raíz buscando hacia arriba el archivo catalogo.js.
# ------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    current = start
    for _ in range(8):
        if (current / "catalogo.js").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError(
        f"No se encontró catalogo.js subiendo desde {start}. "
        "Revisá que la carpeta del Panel Admin esté adentro del repo de la tienda "
        "(TiendaZapasOficial)."
    )


if getattr(sys, "frozen", False):
    # Corriendo como .exe empaquetado con PyInstaller: usar la carpeta
    # donde vive el .exe, no la carpeta temporal de extracción.
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(sys._MEIPASS)  # templates/static empaquetados adentro
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

REPO_ROOT = find_repo_root(BASE_DIR)
FOTOS_DIR = REPO_ROOT / "Fotos"
CATALOGO_JS = REPO_ROOT / "catalogo.js"
ZAPATILLAS_MANUAL_JS = REPO_ROOT / "zapatillas_manual.js"
INDUMENTARIA_JS = REPO_ROOT / "indumentaria.js"

EXTENSIONES_FOTO = [".jpg", ".jpeg", ".png", ".webp"]

app = Flask(
    __name__,
    template_folder=str(RESOURCE_DIR / "templates"),
    static_folder=str(RESOURCE_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB por foto


# ------------------------------------------------------------------
# Mismas reglas que usan piloto_automatico.py / bot_whatsapp.py para
# calcular el nombre de archivo de foto a partir del nombre del modelo.
# ------------------------------------------------------------------

def limpiar_nombre_archivo(nombre: str) -> str:
    if not nombre:
        return ""
    nombre_limpio = nombre.replace("/", " ").replace("\\", " ").replace("\u00a0", " ")
    return " ".join(nombre_limpio.split())


def buscar_foto_existente(nombre_modelo: str):
    nombre_archivo = limpiar_nombre_archivo(nombre_modelo)
    for ext in EXTENSIONES_FOTO:
        ruta = FOTOS_DIR / f"{nombre_archivo}{ext}"
        if ruta.exists():
            return f"Fotos/{nombre_archivo}{ext}"
    return None


# ------------------------------------------------------------------
# Parser / escritor para zapatillas_manual.js, indumentaria.js y,
# en modo solo-lectura, catalogo.js. Todos comparten el mismo formato:
#   { modelo: 'Nombre', talles: [{"talle": N, "stock": N}, ...], foto: 'Fotos/x.jpg' },
# El array de talles ya usa comillas dobles -> es JSON válido tal cual.
# ------------------------------------------------------------------

OBJ_PATTERN = re.compile(
    r"\{\s*modelo:\s*'((?:[^'\\]|\\.)*)'\s*,\s*talles:\s*(\[.*?\])\s*,\s*foto:\s*'((?:[^'\\]|\\.)*)'\s*\}",
    re.DOTALL,
)


def parsear_stock_js(path: Path):
    if not path.exists():
        return []
    contenido = path.read_text(encoding="utf-8")
    productos = []
    for match in OBJ_PATTERN.finditer(contenido):
        modelo, talles_raw, foto = match.groups()
        try:
            talles = json.loads(talles_raw)
        except json.JSONDecodeError:
            talles = []
        productos.append(
            {
                "modelo": modelo.replace("\\'", "'"),
                "talles": talles,
                "foto": foto.replace("\\'", "'"),
            }
        )
    return productos


def escapar_js_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def escribir_stock_js(path: Path, productos: list, nombre_variable: str, encabezado: str):
    productos_ordenados = sorted(productos, key=lambda p: p["modelo"].lower())
    lineas = [encabezado.rstrip(), "", f"const {nombre_variable} = ["]
    for p in productos_ordenados:
        talles_json = json.dumps(p["talles"], ensure_ascii=False)
        modelo = escapar_js_string(p["modelo"])
        foto = escapar_js_string(p["foto"])
        lineas.append(f"    {{ modelo: '{modelo}', talles: {talles_json}, foto: '{foto}' }},")
    lineas.append("];\n")
    path.write_text("\n".join(lineas), encoding="utf-8")


ENCABEZADO_ZAPATILLAS_MANUAL = (
    "// Stock de zapatillas que NO se sacan de la tienda online (piloto_automatico.py\n"
    "// nunca escribe ni pisa este archivo). Editado desde el Panel Admin."
)
ENCABEZADO_INDUMENTARIA = "// Stock de indumentaria cargado a mano. Editado desde el Panel Admin."

TIPOS_STOCK = {
    "zapatillas": (ZAPATILLAS_MANUAL_JS, "stock_zapatillas_manual", ENCABEZADO_ZAPATILLAS_MANUAL),
    "indumentaria": (INDUMENTARIA_JS, "stock_indumentaria", ENCABEZADO_INDUMENTARIA),
}


def resolver_tipo(tipo: str):
    if tipo not in TIPOS_STOCK:
        raise ValueError(f"Tipo de stock inválido: {tipo}")
    return TIPOS_STOCK[tipo]


# ------------------------------------------------------------------
# Rutas: páginas
# ------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", repo_root=str(REPO_ROOT))


# ------------------------------------------------------------------
# Rutas: dashboard (catalogo.js del scraper, solo lectura)
# ------------------------------------------------------------------

@app.route("/api/dashboard")
def api_dashboard():
    catalogo = parsear_stock_js(CATALOGO_JS)
    faltantes = [p["modelo"] for p in catalogo if not buscar_foto_existente(p["modelo"])]
    return jsonify(
        {
            "total_catalogo": len(catalogo),
            "faltan_foto": faltantes,
            "cantidad_faltan": len(faltantes),
        }
    )


# ------------------------------------------------------------------
# Rutas: stock manual (zapatillas / indumentaria) - CRUD
# ------------------------------------------------------------------

@app.route("/api/stock/<tipo>", methods=["GET"])
def api_stock_get(tipo):
    try:
        path, _, _ = resolver_tipo(tipo)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    productos = parsear_stock_js(path)
    for p in productos:
        p["tiene_foto"] = bool(buscar_foto_existente(p["modelo"]))
    return jsonify(productos)


@app.route("/api/stock/<tipo>", methods=["POST"])
def api_stock_save(tipo):
    try:
        path, varname, encabezado = resolver_tipo(tipo)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    data = request.get_json(force=True) or {}
    modelo_original = (data.get("modelo_original") or "").strip()
    modelo = (data.get("modelo") or "").strip()
    talles = data.get("talles") or []
    foto = data.get("foto")

    if not modelo:
        return jsonify({"error": "El nombre del modelo es obligatorio."}), 400
    if not isinstance(talles, list) or len(talles) == 0:
        return jsonify({"error": "Agregá al menos un talle con stock."}), 400

    productos = parsear_stock_js(path)

    if not foto:
        foto = buscar_foto_existente(modelo) or f"Fotos/{limpiar_nombre_archivo(modelo)}.jpg"

    nuevo = {"modelo": modelo, "talles": talles, "foto": foto}

    clave_a_borrar = modelo_original if modelo_original else modelo
    productos = [p for p in productos if p["modelo"] != clave_a_borrar]
    productos.append(nuevo)

    escribir_stock_js(path, productos, varname, encabezado)
    return jsonify({"ok": True, "producto": nuevo})


@app.route("/api/stock/<tipo>/<path:modelo>", methods=["DELETE"])
def api_stock_delete(tipo, modelo):
    try:
        path, varname, encabezado = resolver_tipo(tipo)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    productos = parsear_stock_js(path)
    nuevos = [p for p in productos if p["modelo"] != modelo]
    if len(nuevos) == len(productos):
        return jsonify({"error": "No se encontró ese modelo."}), 404

    escribir_stock_js(path, nuevos, varname, encabezado)
    return jsonify({"ok": True})


# ------------------------------------------------------------------
# Rutas: fotos
# ------------------------------------------------------------------

@app.route("/api/upload-foto", methods=["POST"])
def api_upload_foto():
    modelo = (request.form.get("modelo") or "").strip()
    archivo = request.files.get("foto")
    if not modelo or not archivo or archivo.filename == "":
        return jsonify({"error": "Falta el modelo o el archivo de foto."}), 400

    ext = Path(archivo.filename).suffix.lower()
    if ext not in EXTENSIONES_FOTO:
        return jsonify({"error": f"Extensión no permitida: {ext}. Usá jpg, jpeg, png o webp."}), 400

    FOTOS_DIR.mkdir(exist_ok=True)
    nombre_archivo = limpiar_nombre_archivo(modelo)

    # Si ya existía una foto con otra extensión para el mismo modelo, la
    # sacamos para no dejar fotos viejas colgadas.
    for otra_ext in EXTENSIONES_FOTO:
        if otra_ext != ext:
            vieja = FOTOS_DIR / f"{nombre_archivo}{otra_ext}"
            if vieja.exists():
                vieja.unlink()

    ruta_destino = FOTOS_DIR / f"{nombre_archivo}{ext}"
    archivo.save(ruta_destino)
    return jsonify({"ok": True, "foto": f"Fotos/{nombre_archivo}{ext}"})


@app.route("/Fotos/<path:nombre>")
def servir_foto(nombre):
    # OJO: tiene que ser "/Fotos/" con mayúscula, igual que el valor guardado
    # en el campo "foto" de cada producto (ej: "Fotos/Nike super star.jpeg").
    # Las rutas en Flask son sensibles a mayúsculas/minúsculas.
    return send_from_directory(FOTOS_DIR, nombre)


# ------------------------------------------------------------------
# Rutas: publicar cambios a GitHub (manual, a pedido)
# ------------------------------------------------------------------
# Nota: el control de piloto_automatico.py y bot_whatsapp.py ya no vive acá.
# Ahora son accesos directos de escritorio propios (ver automatizacion/).

@app.route("/api/git/status")
def api_git_status():
    try:
        resultado = subprocess.run(
            ["git", "status", "--short"], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    cambios = [l for l in resultado.stdout.strip().splitlines() if l.strip()]
    return jsonify({"cambios": cambios})


@app.route("/api/git/publicar", methods=["POST"])
def api_git_publicar():
    pasos = []
    try:
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        pasos.append("git pull: ok")

        subprocess.run(
            ["git", "add", "Fotos", "zapatillas_manual.js", "indumentaria.js","index.html", "minorista.html", "mezclar_stock.js"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
)
        pasos.append("git add: ok")

        mensaje = f"Actualización manual desde Panel Admin ({datetime.now().strftime('%d/%m %H:%M')})"
        commit = subprocess.run(
            ["git", "commit", "-m", mensaje], cwd=str(REPO_ROOT), capture_output=True, text=True
        )
        if "nothing to commit" in (commit.stdout + commit.stderr):
            return jsonify({"ok": True, "mensaje": "No había cambios pendientes para publicar.", "pasos": pasos})
        pasos.append("git commit: ok")

        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
        )
        pasos.append("git push: ok")

        return jsonify(
            {"ok": True, "mensaje": "¡Listo! Los cambios ya están publicados en GitHub Pages.", "pasos": pasos}
        )
    except subprocess.CalledProcessError as e:
        detalle = (e.stderr or e.stdout or str(e)).strip()
        return jsonify({"ok": False, "error": detalle, "pasos": pasos}), 500


if __name__ == "__main__":
    import webbrowser
    import atexit

    PUERTO = 5151

    # Guardamos nuestro propio PID. Como el acceso directo del escritorio
    # corre esto oculto (sin ventana), detener_panel.bat necesita este
    # archivo para saber a qué proceso apagar.
    PID_FILE = BASE_DIR / "panel.pid"
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def _limpiar_pid():
        try:
            PID_FILE.unlink()
        except Exception:
            pass

    atexit.register(_limpiar_pid)

    print(f"Repo detectado en: {REPO_ROOT}")
    print(f"Abriendo el Panel Admin en http://127.0.0.1:{PUERTO} ...")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}")).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
