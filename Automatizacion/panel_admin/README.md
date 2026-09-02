# Panel Admin - Tienda Zapas

> Para la instalación completa (accesos directos, piloto, bot de WhatsApp)
> ver el `README.md` en la raíz del repo. Esto de acá es solo sobre el
> panel en sí.

App web local para dejar de editar `zapatillas_manual.js` /
`indumentaria.js` a mano. Corre en tu propia PC, no se sube a ningún lado
ni queda expuesta a internet.

## Qué hace

1. **Inicio**: te muestra qué productos escaneados del proveedor
   (`catalogo.js`) todavía no tienen foto en `Fotos/`, y subís la foto ahí
   mismo. Se refresca sola cada 20 segundos.
2. **Stock manual - Zapatillas / Indumentaria**: agregar, editar y borrar
   modelos con un formulario (nombre, foto, talles y stock), con la
   miniatura de cada modelo a la vista. Escribe `zapatillas_manual.js` /
   `indumentaria.js` con el mismo formato exacto que ya usan `tienda.js` y
   `minorista.js`, así que no rompe nada de la lógica de precios ni de
   talles bi-numerales de ojotas.
3. **Publicar cambios**: botón manual que hace `git add / commit / push`
   de `Fotos/`, `zapatillas_manual.js` e `indumentaria.js`.

> `catalogo.js` **no se edita** desde el panel: eso lo sigue generando
> únicamente `piloto_automatico.py`.
>
> El manejo de `piloto_automatico.py` y `bot_whatsapp.py` ya no está acá
> adentro — son accesos directos propios del Escritorio. Ver el README de
> la raíz del repo.

## Dos formas de arrancarlo

- **`iniciar_panel_silencioso.vbs`**: sin consola, para uso diario (es a
  lo que apunta el acceso directo del Escritorio).
- **`iniciar_panel.bat`**: con consola visible, útil la primera vez o si
  algo no anda y necesitás ver el error.

Para apagarlo: `detener_panel.bat` (si lo abriste con el `.vbs` silencioso,
no hay ventana para cerrar con la X, así que es la única forma).

## Notas técnicas

- Al editar/agregar un modelo, el archivo `.js` correspondiente se
  reescribe completo y ordenado alfabéticamente — el formato de cada línea
  es idéntico al que ya tenías, así que `esModeloOjota()`,
  `PRECIOS_ESPECIFICOS`, etc. en `tienda.js` / `minorista.js` siguen
  funcionando igual.
- El puerto usado es `5151`. Si algo más lo está usando en tu PC, cambiá
  la línea `PUERTO = 5151` en `app.py`.
- Al arrancar, `app.py` escribe su propio PID en `panel.pid` (adentro de
  esta misma carpeta) para que `detener_panel.bat` sepa a qué proceso
  apagar cuando corre oculto.

### ¿Y si quiero un .exe de verdad?

Con los accesos directos silenciosos ya tenés el mismo resultado (ícono,
sin consola) sin compilar nada. Si igual querés un `.exe` compilado,
`build_exe.bat` sigue disponible (necesita `pip install pyinstaller`, lo
hace solo). Igual vas a necesitar Python instalado aparte en la PC, porque
`piloto_automatico.py` y `bot_whatsapp.py` siguen siendo scripts de Python
normales.
