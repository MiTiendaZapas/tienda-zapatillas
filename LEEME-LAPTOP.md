# Instrucciones para la laptop: pasar al piloto automático nuevo

> Para Claude en la laptop: leé todo este archivo antes de hacer nada. Escribile
> al usuario **siempre en español**, contándole cada paso. No modifiques otros
> archivos del repositorio ni la tienda: solo lo que se pide acá.

## Qué cambió (27/09/2026)

La tienda se mudó. Ya está publicada y funcionando:

| Tienda | Link |
|---|---|
| Minorista (público) | https://mitiendazapas.github.io |
| Revendedores | https://mitiendazapas.github.io/mayorista |
| ClienteA | https://mitiendazapas.github.io/fo y /fo/mayorista |

- La tienda nueva vive en el repositorio **MiTiendaZapas/mitiendazapas.github.io**.
- El catálogo sale del **proveedor nuevo** (https://vestite-piola.vercel.app, por su API).
- Este repositorio (`TiendaZapasOficial`) quedó con redirecciones a los links nuevos.
  Se sigue usando para el **stock de casa** que guarda el Panel Admin
  (`zapatillas_manual.js`, `indumentaria.js` y `Fotos/`).
- El piloto viejo (`Automatizacion/piloto_automatico.py`) actualiza `catalogo.js`,
  que **ya no usa ninguna tienda**. Hay que reemplazarlo por el piloto nuevo.

## Pasos

### 1. Apagar el piloto viejo
- Cerrá su ventana, o ejecutá `Automatizacion\detener_piloto.bat`.
- Si arranca solo al prender la laptop (acceso directo en la carpeta de Inicio de
  Windows, `shell:startup`, o una tarea programada), **quitalo** de ahí. No borres el
  archivo del piloto viejo: queda guardado por si hay que volver atrás.

### 2. Traer lo último de este repositorio
En la carpeta `TiendaZapasOficial`:
```
git pull --rebase --autostash
```

### 3. Descargar el repositorio nuevo **al lado** de `TiendaZapasOficial`
Tiene que quedar en la **misma carpeta que contiene a `TiendaZapasOficial`**
(el piloto nuevo busca el stock de casa en `..\TiendaZapasOficial`):
```
cd <carpeta que contiene TiendaZapasOficial>
git clone https://github.com/MiTiendaZapas/mitiendazapas.github.io.git
```
Quedaría así:
```
proyectos\
├── TiendaZapasOficial\          (Panel Admin, stock de casa)
└── mitiendazapas.github.io\     (tienda nueva + piloto nuevo)
```

### 4. Instalar lo necesario
```
pip install pillow
```
(Pillow convierte las fotos. El resto del piloto usa solo Python estándar.)

### 5. Probar una vuelta sin publicar
En la carpeta `mitiendazapas.github.io`:
```
python sincronizador\sync_catalog.py --dry-run
```
Tiene que decir `Proveedor activo: vestite_api`, la cantidad de modelos y
`Modelos de stock de casa: N` (si dice 0, el paso 3 quedó en otra carpeta).

### 6. Prender el piloto nuevo
Doble clic en `mitiendazapas.github.io\sincronizador\iniciar_piloto.bat`.

- Actualiza cada 15-20 minutos y descansa de 00:00 a 07:30 (igual que el viejo).
- Sube el catálogo al repositorio nuevo y, si hubo cambios sin publicar del Panel
  Admin, sube el stock de casa a `TiendaZapasOficial`.
- Todo lo que muestra queda en `sincronizador\informes\piloto.log`.
- Para detenerlo: cerrar su ventana o `sincronizador\detener_piloto.bat`.

### 7. Que arranque solo al prender la laptop
Poné un acceso directo a `mitiendazapas.github.io\sincronizador\iniciar_piloto.bat`
en la carpeta de Inicio de Windows (`Win + R` → `shell:startup`), en lugar del
acceso directo del piloto viejo.

### 8. Comprobar que funciona
- En la ventana del piloto aparece `🔄 Catálogo publicado en GitHub.` o
  `⏸️ Sin cambios de stock.`
- En https://github.com/MiTiendaZapas/mitiendazapas.github.io/commits/main aparece un
  commit "Catálogo actualizado a las HH:MM".
- En https://mitiendazapas.github.io/catalogo/productos.json el campo `generatedAt`
  tiene la hora de la última vuelta (puede tardar hasta 10 minutos en verse).

## Si algo falla
- **Error de git al subir** (permisos o sesión): la laptop tiene que tener acceso de
  escritura a los dos repositorios de la cuenta MiTiendaZapas. Probá `git push` a
  mano en `mitiendazapas.github.io` para ver el mensaje.
- **El proveedor no responde**: el piloto deja publicado el catálogo anterior y
  reintenta a los 30 minutos. No hace falta hacer nada.
- **Volver al piloto viejo** (solo si el nuevo no anda): apagar el nuevo y prender
  `Automatizacion\piloto_automatico_visible.bat`. Ojo: el piloto viejo solo actualiza
  la tienda anterior, que ahora redirige a la nueva, así que la tienda nueva no se
  actualizaría. Avisale al usuario.

No hay que tocar el bot de WhatsApp desde la laptop: corre en la otra PC.
