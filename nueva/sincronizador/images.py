"""Descarga y optimización de imágenes de producto (opción A: se guardan en el repo).

Resultado por producto, en catalogo/fotos/<id-producto>/:
    <hash>-lg.webp   todas las fotos de la galería (900px)
    <hash>-sm.webp   solo la portada, para la tarjeta del catálogo (480px)

El <hash> sale de la URL de origen: si el proveedor cambia una foto, cambia el
nombre del archivo y ningún navegador puede quedarse mostrando la vieja.

Protecciones ante imprevistos:
  - Si falla la descarga de un producto, se conservan sus fotos anteriores.
  - Cada archivo se escribe primero como temporal y después se renombra: un
    corte de luz a mitad de camino nunca deja una imagen rota publicada.
  - Si un modelo desaparece del proveedor, sus fotos se borran recién pasados
    IMAGE_KEEP_MISSING_DAYS (por si vuelve en el próximo escaneo).
  - Respuestas que no son imágenes (páginas de error, etc.) se descartan.
  - Reintentos al borrar o renombrar, porque OneDrive o el antivirus pueden
    tener tomado un archivo por unos segundos.
"""
import hashlib
import io
import json
import os
import shutil
import time
from pathlib import Path

from PIL import Image

import net
import settings

STATE_FILE = settings.STATE_DIR / "images.json"
DAY = 86400


def _retry(action, attempts=5):
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(attempt)


def _source_key(source):
    return str(source).split("?")[0]   # las URLs firmadas cambian la query en cada pedido


def _file_name(source_key, size):
    return f"{hashlib.sha1(source_key.encode('utf-8')).hexdigest()[:10]}-{size}.webp"


class ImageStore:
    def __init__(self):
        self.state = {}
        if STATE_FILE.exists():
            try:
                self.state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print("  ⚠️ Memoria de imágenes ilegible: se reconstruye (las fotos ya bajadas se reutilizan).")

    # --- memoria --------------------------------------------------------------
    def save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = STATE_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        _retry(lambda: os.replace(temp, STATE_FILE))

    def mark_seen(self, product_ids):
        now = time.time()
        for product_id in product_ids:
            if product_id in self.state:
                self.state[product_id]["last_seen"] = now

    # --- consulta -------------------------------------------------------------
    def current(self, product_id):
        """Fotos ya publicadas de un producto (si siguen en disco), sin descargar nada."""
        entry = self.state.get(product_id)
        return entry["images"] if entry and self._files_exist(entry["images"]) else []

    def needs_check(self, product_id):
        entry = self.state.get(product_id)
        return (not entry
                or not self._files_exist(entry["images"])
                or time.time() - entry.get("checked", 0) > settings.IMAGE_REFRESH_DAYS * DAY)

    # --- descarga -------------------------------------------------------------
    def update(self, product_id, sources):
        """Procesa las fotos de origen (URLs o rutas locales). Devuelve las publicadas."""
        sources = sources[: settings.MAX_IMAGES_PER_PRODUCT]
        keys = [_source_key(s) for s in sources]
        previous = self.state.get(product_id)

        if previous and previous["sources"] == keys and self._files_exist(previous["images"]):
            previous["checked"] = time.time()
            return previous["images"]

        folder = settings.IMAGES_DIR / product_id
        folder.mkdir(parents=True, exist_ok=True)
        images = []
        for source, key in zip(sources, keys):
            try:
                images.append(self._process(source, key, folder, is_cover=not images))
            except Exception as error:
                print(f"    ⚠️ Foto descartada ({product_id}): {error}")

        if not images:
            print(f"    ⚠️ Ninguna foto nueva de {product_id}: se mantienen las anteriores.")
            return self.current(product_id)

        keep = {Path(img[size]).name for img in images for size in ("sm", "lg") if size in img}
        for file in folder.iterdir():
            if file.name not in keep:
                _retry(file.unlink)

        self.state[product_id] = {
            "sources": keys, "images": images,
            "checked": time.time(), "last_seen": time.time(),
        }
        return images

    def _process(self, source, key, folder, is_cover):
        lg_path = folder / _file_name(key, "lg")
        sm_path = folder / _file_name(key, "sm")
        if lg_path.exists() and (sm_path.exists() or not is_cover):
            with Image.open(lg_path) as existing:     # ya estaba: se reutiliza sin descargar
                width, height = existing.size
        else:
            data = source.read_bytes() if isinstance(source, Path) else net.fetch_bytes(source)
            original = self._open_as_rgb(data)
            width, height = self._save(original, lg_path, settings.IMAGE_LG_PX)
            if is_cover:
                self._save(original, sm_path, settings.IMAGE_SM_PX)

        image = {"lg": self._relative(lg_path), "w": width, "h": height}
        if is_cover:
            image["sm"] = self._relative(sm_path)
        return image

    # --- limpieza -------------------------------------------------------------
    def cleanup(self, current_ids):
        """Borra fotos de modelos ausentes hace más de IMAGE_KEEP_MISSING_DAYS y carpetas huérfanas."""
        limit = time.time() - settings.IMAGE_KEEP_MISSING_DAYS * DAY
        for product_id in list(self.state):
            if product_id not in current_ids and self.state[product_id].get("last_seen", 0) < limit:
                _retry(lambda: shutil.rmtree(settings.IMAGES_DIR / product_id, ignore_errors=True))
                del self.state[product_id]
        if settings.IMAGES_DIR.exists():
            for folder in settings.IMAGES_DIR.iterdir():
                if folder.is_dir() and folder.name not in self.state:
                    _retry(lambda: shutil.rmtree(folder, ignore_errors=True))
                elif folder.is_file() and folder.suffix == ".tmp":
                    _retry(folder.unlink)

    @staticmethod
    def total_mb():
        if not settings.IMAGES_DIR.exists():
            return 0.0
        return sum(f.stat().st_size for f in settings.IMAGES_DIR.rglob("*.webp")) / 1024 / 1024

    # --- utilidades -----------------------------------------------------------
    @staticmethod
    def _files_exist(images):
        return bool(images) and all(
            (settings.CATALOG_DIR / img[size]).exists() for img in images for size in ("sm", "lg") if size in img)

    @staticmethod
    def _relative(path):
        return path.relative_to(settings.CATALOG_DIR).as_posix()

    @staticmethod
    def _open_as_rgb(data):
        image = Image.open(io.BytesIO(data))   # lanza error si no es una imagen
        image.load()
        if image.mode == "RGB":
            return image
        background = Image.new("RGB", image.size, "white")
        rgba = image.convert("RGBA")
        background.paste(rgba, mask=rgba)
        return background

    @staticmethod
    def _save(original, path, box):
        copy = original.copy()
        copy.thumbnail((box, box), Image.LANCZOS)   # nunca agranda
        temp = path.with_name(path.name + ".tmp")
        copy.save(temp, "WEBP", quality=settings.IMAGE_QUALITY, method=6)
        _retry(lambda: os.replace(temp, path))
        return copy.size
