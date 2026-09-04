const TU_NUMERO = "5491153773771"; 
let carrito = [];

// ============================================================
// PRECIOS ESPECÍFICOS POR MODELO
// ============================================================
// Para sumar un producto NUEVO con precio propio (uno que vos nombrás
// siempre exactamente igual, ej. en indumentaria.js), agregá UNA línea acá.
// La clave es el nombre EXACTO del modelo, en minúsculas. Se compara
// completo (no por substring), así nunca puede chocar con otro modelo
// que contenga las mismas palabras sueltas (ej: "mind gris" acá adentro
// nunca matchea con "Nike mind gris", porque el string completo es distinto).
//
// Si en cambio el producto viene del bot scraper y el nombre puede variar
// un poco cada vez, no uses este diccionario: agregá una regla de palabras
// combinadas más abajo, como la de "NB 9060 nuevas brillo" (9060 + brillo).
const PRECIOS_ESPECIFICOS = {
    "mind beige":   { unidad: 40000, mayor: 35000 },
    "mind gris":    { unidad: 40000, mayor: 35000 },
    "mind negras":  { unidad: 40000, mayor: 35000 },
    "mind blancas": { unidad: 40000, mayor: 35000 },
    // "tl1 negras" ya NO va acá: se sacó de este diccionario para que el
    // precio de TL1 siga siempre al de shox automáticamente (ver la palabra
    // "shox" más abajo en obtenerPrecioMinorista y obtenerPrecioMayorista,
    // donde ahora también matchea "tl1"). Así, si el día de mañana cambia el
    // precio de shox, TL1 cambia solo con eso, sin tener que tocar acá.
};

// Modelos que, aunque no tengan la palabra "ojotas" en el nombre, se
// venden y se muestran como ojotas (talles bi-numerales tipo 39/40, 41/42).
const MODELOS_OJOTAS_BINUMERAL = ["mind beige", "mind gris", "mind negras", "mind blancas"];

function esModeloOjota(modelo) {
    const m = modelo.toLowerCase().trim();
    return m.includes("ojotas") || MODELOS_OJOTAS_BINUMERAL.includes(m);
}

function obtenerPrecioMinorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase().trim();

    if (PRECIOS_ESPECIFICOS[nombre]) {
        return PRECIOS_ESPECIFICOS[nombre].unidad;
    }

    // EXCEPCIÓN DE INDUMENTARIA (Precio por unidad)
    if (nombre.includes("remera")) {
        return 20000;
    }
    if (nombre.includes("baggy nk")) {
        return 28000;
    }

    // EXCEPCIÓN DE TODAS LAS OJOTAS ($40.000 por unidad)
    if (nombre.includes("ojotas")) {
        return 40000;
    }

    // EXCEPCIÓN DE NIÑO POR UNIDAD ($35.000)
    if (nombre.includes("niño") || nombre.includes("niños")) {
        return 35000;
    }

    // JORDAN LOW PINK ($55.000 por unidad)
    if (nombre.includes("jordan low pink") || nombre.includes("jordan pink low")) {
        return 55000;
    }

    // JORDAN 11 SUELA AZUL ($65.000 por unidad)
    if (nombre.includes("jordan 11 suela azul")) {
        return 65000;
    }

    // JORDAN 11 SUELA CELESTE ($65.000 por unidad)
    if (nombre.includes("jordan 11 suela celeste")) {
        return 65000;
    }

    // RETRO 11 PANDA Y JORDAN 11 SUELA BLANCA ($65.000 por unidad)
    if (nombre.includes("retro 11 panda") || nombre.includes("jordan 11 suela blanca")) {
        return 65000;
    }

    // MODELOS ESPECÍFICOS A $60.000 POR UNIDAD (Incluyendo Nike V5 rosa)
    if (nombre.includes("nike v5 blancas") || 
        nombre.includes("nike v5 negras") || 
        nombre.includes("nike v5 rosa") ||
        nombre.includes("air jordan pipa gris") || 
        nombre.includes("air jordan black") || 
        nombre.includes("new balance 4000") ||
        nombre.includes("nb 4000")) {
        return 60000;
    }

    // 1. PRECIOS DE $60.000
    if (nombre.includes("adidas 2000") || 
        nombre.includes("air forcé con medias") || 
        nombre.includes("air force con medias") || 
        nombre.includes("puma 180") || 
        nombre.includes("campus") || 
        nombre.includes("shox") || 
        nombre.includes("tl1") ||
        nombre.includes("haylan") || 
        nombre.includes("vans haylan") ||
        nombre.includes("forum verde summer") ||
        nombre.includes("jordan low 1 diamond") ||
        nombre.includes("super star brillo") ||
        nombre.includes("súper star brillo") ||
        nombre.includes("super star brillo perla") ||
        nombre.includes("súper star brillo perla") ||
        nombre.includes("jordan diamond pipa blanca") ||
        nombre.includes("jordan pink") ||
        nombre.includes("negras medias") ||
        nombre.includes("jordan 1 brillosa") || 
        nombre.includes("jordan 11 negra/blanca") ||
        nombre.includes("jordan 11 negra blanca") ||
        nombre.includes("exclusivas white")) {
        return 60000;
    }

    // NB 9060 NUEVAS BRILLO ($60.000 unidad minorista) - antes de la regla
    // genérica de "9060" para no pisar otros modelos 9060 (suela rosa, celeste).
    if (nombre.includes("9060") && nombre.includes("brillo")) {
        return 60000;
    }

    // 2. PRECIOS DE $55.000 (Incluyendo todas las NB 530)
    if (nombre.includes("530") ||
        nombre.includes("retro 4") || 
        nombre.includes("retro 1") || 
        nombre.includes("jordan low glister") || 
        nombre.includes("jordan") || 
        nombre.includes("abzorb") || 
        nombre.includes("9060") || 
        nombre.includes("running") || 
        nombre.includes("nova") || 
        nombre.includes("new balance")) {
        return 55000;
    }

    // 3. PRECIOS DE $50.000 (Por defecto para el resto)
    return 50000;
}

function obtenerPrecioMayorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase().trim();

    if (PRECIOS_ESPECIFICOS[nombre]) {
        return PRECIOS_ESPECIFICOS[nombre].mayor;
    }

    // 1. EXCEPCIONES MUY ESPECÍFICAS
    if (nombre.includes("ojotas")) {
        return 31000;
    }

    // CUALQUIER MODELO CON "BRILLO" EN EL NOMBRE ($42.000 por mayor)
    if (nombre.includes("brillo")) {
        return 42000;
    }

    if (nombre.includes("botitas jordan niño") || nombre.includes("niño") || nombre.includes("niños")) {
        return 30000;
    }

    if (nombre.includes("jordan low pink") || nombre.includes("jordan pink low")) {
        return 39000;
    }

    // RETRO 11 PANDA Y JORDAN 11 SUELA BLANCA POR MAYOR ($50.000)
    if (nombre.includes("retro 11 panda") || nombre.includes("jordan 11 suela blanca")) {
        return 50000;
    }

    // JORDAN 11 SUELA CELESTE POR MAYOR ($50.000)
    if (nombre.includes("jordan 11 suela celeste")) {
        return 50000;
    }

    // MODELOS ESPECÍFICOS A $42.000 POR MAYOR
    if (nombre.includes("nike v5 blancas") || 
        nombre.includes("nike v5 negras") || 
        nombre.includes("nike v5 rosa") ||
        nombre.includes("air jordan pipa gris") || 
        nombre.includes("air jordan black") || 
        nombre.includes("new balance 4000") ||
        nombre.includes("nb 4000")) {
        return 42000;
    }

    // PRECIOS DE 50.000
    if (nombre.includes("jordan 11 suela azul") ||
        nombre.includes("jordan 11 negra/blanca") ||
        nombre.includes("jordan 11 negra blanca")) {
        return 50000;
    }

    // PRECIOS DE 42.000
    if (nombre.includes("forum verde summer") || 
        nombre.includes("jordan low 1 diamond") || 
        nombre.includes("jordan diamond pipa blanca") || 
        nombre.includes("jordan pink") || 
        nombre.includes("adidas 2000") || 
        nombre.includes("puma 180") || 
        nombre.includes("campus") ||
        nombre.includes("shox") ||
        nombre.includes("tl1") ||
        nombre.includes("haylan")) {
        return 42000;
    }

    // PRECIOS DE 41.000
    if (nombre.includes("exclusivas white") || 
        nombre.includes("negras medias") || 
        nombre.includes("air forcé con medias") || 
        nombre.includes("air force con medias")) {
        return 41000;
    }

    // PRECIOS DE 39.000
    if (nombre.includes("samba classic") ||
        nombre.includes("jordan low glister") ||
        nombre.includes("jordan") || 
        nombre.includes("retro 4") || 
        nombre.includes("botitas") ||
        nombre.includes("530") || 
        nombre.includes("9060") || 
        nombre.includes("abzorb") || 
        nombre.includes("running") || 
        nombre.includes("mind")) {
        return 39000;
    }

    // 2. CATEGORÍAS GENERALES Y PRECIOS DE 37.000
    if (nombre.includes("samba total black") || 
        nombre.includes("adidas boas") || 
        nombre.includes("botitas vans") || 
        nombre.includes("glister beige pipa marrón") ||
        nombre.includes("air forcé") || nombre.includes("air force") ||
        nombre.includes("forum") || nombre.includes("fórum") ||
        nombre.includes("super star") || nombre.includes("súper star") || 
        nombre.includes("glistter") || nombre.includes("glitter") || nombre.includes("glister") || 
        nombre.includes("dunk pombo") || nombre.includes("dunk total black") || 
        nombre.includes("combinada celeste") || nombre.includes("sb dunk") || nombre.includes("dunk") ||
        nombre.includes("vans") || nombre.includes("knu") ||
        nombre.includes("puma") ||
        nombre.includes("deportivas fit")) {
        return 37000;
    }
    
    // Precio por defecto si un producto nuevo no entra en ninguna lista
    return 37000; 
}

function procesarTallesOjota(tallesArray) {
    if (!tallesArray || tallesArray.length === 0) return [];
    let tallesProcesados = [];
    let numeros = tallesArray.map(t => parseInt(t.talle !== undefined ? t.talle : t)).filter(n => !isNaN(n));
    numeros.sort((a, b) => a - b);

    for (let i = 0; i < numeros.length; i += 2) {
        if (i + 1 < numeros.length) {
            tallesProcesados.push({ talle: `${numeros[i]}/${numeros[i+1]}`, stock: 99 });
        } else {
            tallesProcesados.push({ talle: `${numeros[i]}`, stock: 99 });
        }
    }
    return tallesProcesados;
}

function cargarProductos() {
    const grid = document.getElementById('grid-productos');
    grid.innerHTML = '';

    if (typeof stock_actualizado === 'undefined') {
        grid.innerHTML = '<h3 style="color:red;">Error: No se encontró el catálogo.</h3>';
        return;
    }

    stock_actualizado.forEach((producto, index) => {
        if(!producto.talles || producto.talles.length === 0) return;

        let listaTallesFinal = esModeloOjota(producto.modelo) 
            ? procesarTallesOjota(producto.talles) 
            : producto.talles;

        let botonesTalles = listaTallesFinal.map(t => {
            let numeroTalle = t.talle !== undefined ? t.talle : t;
            let cantidadStock = t.stock !== undefined ? t.stock : 99;
            let sinStockClass = cantidadStock <= 0 ? 'disabled' : '';
            let disabledAttr = cantidadStock <= 0 ? 'disabled' : '';

            return `<button type="button" class="talle-cuadro ${sinStockClass}" data-talle="${numeroTalle}" data-stock="${cantidadStock}" ${disabledAttr} onclick="seleccionarTalle(${index}, '${numeroTalle}', ${cantidadStock}, this)">${numeroTalle}</button>`;
        }).join('');

        let precioMinorista = obtenerPrecioMinorista(producto.modelo);
        let esIndumentaria = producto.modelo.toLowerCase().includes("remera") || producto.modelo.toLowerCase().includes("baggy nk");
        let textoMayoristaHtml = "";

        if (esIndumentaria) {
            let precioMayInd = producto.modelo.toLowerCase().includes("remera") ? 15000 : 22000;
            textoMayoristaHtml = `<div style="font-size: 12px; color: #28a745; margin-bottom: 6px; font-weight: bold;">Llevando 10 o más: $${precioMayInd.toLocaleString('es-AR')}</div>`;
        } else {
            let precioMayorista = obtenerPrecioMayorista(producto.modelo);
            textoMayoristaHtml = `<div style="font-size: 12px; color: #28a745; margin-bottom: 6px; font-weight: bold;">Llevando 5 o más: $${precioMayorista.toLocaleString('es-AR')}</div>`;
        }

        grid.innerHTML += `
            <div class="producto-card" data-modelo="${producto.modelo.toLowerCase()}">
                <div class="img-container">
                    <img src="${producto.foto}" alt="${producto.modelo}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="sin-foto">📸<br>Falta Imagen</div>
                </div>
                <div class="info-prod">
                    <div class="titulo">${producto.modelo}</div>
                    <div style="font-size: 20px; font-weight: bold; color: #111; margin-top: 2px; margin-bottom: 2px;">
                        $${precioMinorista.toLocaleString('es-AR')}
                    </div>
                    ${textoMayoristaHtml}
                    
                    <div class="talles-grid-container" id="talles-container-${index}">
                        ${botonesTalles}
                    </div>
                    
                    <div style="margin-top: auto;">
                        <div class="fila-cantidad">
                            <div class="control-cant">
                                <button class="btn-qty" onclick="cambiarCantidad(${index}, -1)" id="btn-menos-${index}" disabled>-</button>
                                <span class="num-qty" id="cant-${index}">1</span>
                                <button class="btn-qty" onclick="cambiarCantidad(${index}, 1)" id="btn-mas-${index}" disabled>+</button>
                            </div>
                            <span id="label-stock-${index}" class="stock-disponible">Elegí talle</span>
                        </div>

                        <button id="btn-${index}" class="add-btn" onclick="agregarAlCarrito(${index})" disabled>Seleccionar Talle</button>
                    </div>
                </div>
            </div>
        `;
    });
}

function filtrarCatalogo() {
    const texto = document.getElementById('buscador').value.toLowerCase();
    const tarjetas = document.querySelectorAll('.producto-card');
    
    tarjetas.forEach(tarjeta => {
        const modelo = tarjeta.getAttribute('data-modelo');
        if (modelo.includes(texto)) {
            tarjeta.style.display = '';
        } else {
            tarjeta.style.display = 'none';
        }
    });
}

function seleccionarTalle(index, talle, stockMax, elementoBtn) {
    const contenedor = document.getElementById(`talles-container-${index}`);
    contenedor.querySelectorAll('.talle-cuadro').forEach(b => b.classList.remove('seleccionado'));
    elementoBtn.classList.add('seleccionado');

    contenedor.setAttribute('data-talle-seleccionado', talle);
    contenedor.setAttribute('data-stock-max', stockMax);

    const btn = document.getElementById(`btn-${index}`);
    const displayCant = document.getElementById(`cant-${index}`);
    
    displayCant.textContent = "1";
    document.getElementById(`btn-menos-${index}`).disabled = true;
    document.getElementById(`btn-mas-${index}`).disabled = (stockMax <= 1);
    
    btn.disabled = false;
    btn.textContent = "Agregar al Pedido";

    const labelStock = document.getElementById(`label-stock-${index}`);
    if (stockMax >= 99) {
        labelStock.textContent = "¡Disponible!";
        labelStock.className = "stock-disponible sobra";
    } else {
        labelStock.textContent = `Quedan ${stockMax}`;
        labelStock.className = "stock-disponible";
    }
}

function cambiarCantidad(index, cambio) {
    const contenedor = document.getElementById(`talles-container-${index}`);
    const stockMax = parseInt(contenedor.getAttribute('data-stock-max')) || 99;
    
    const displayCant = document.getElementById(`cant-${index}`);
    let cantActual = parseInt(displayCant.textContent);
    let nuevaCant = cantActual + cambio;

    if (nuevaCant >= 1 && nuevaCant <= stockMax) {
        displayCant.textContent = nuevaCant;
    }

    document.getElementById(`btn-menos-${index}`).disabled = (nuevaCant <= 1);
    document.getElementById(`btn-mas-${index}`).disabled = (nuevaCant >= stockMax);
}

function agregarAlCarrito(indexProd) {
    const contenedor = document.getElementById(`talles-container-${indexProd}`);
    const talleElegido = contenedor.getAttribute('data-talle-seleccionado');
    
    if (!talleElegido) {
        alert("Por favor, elegí un talle primero.");
        return;
    }

    const stockMax = parseInt(contenedor.getAttribute('data-stock-max'));
    const cantidadDeseada = parseInt(document.getElementById(`cant-${indexProd}`).textContent);

    const prod = stock_actualizado[indexProd];
    const talleNumero = talleElegido; 
    
    const itemExistente = carrito.find(item => item.modelo === prod.modelo && item.talle === talleNumero);
    
    if (itemExistente) {
        if (itemExistente.cantidad + cantidadDeseada > stockMax) {
            alert(`Solo hay ${stockMax} pares de este talle. Ya tenés ${itemExistente.cantidad} en tu pedido.`);
            return;
        }
        itemExistente.cantidad += cantidadDeseada;
    } else {
        carrito.push({
            modelo: prod.modelo,
            talle: talleNumero,
            cantidad: cantidadDeseada
        });
    }

    carrito.sort((a, b) => {
        if (a.modelo < b.modelo) return -1;
        if (a.modelo > b.modelo) return 1;
        return String(a.talle).localeCompare(String(b.talle));
    });

    actualizarCarrito();

    const btnAdd = document.getElementById(`btn-${indexProd}`);
    const textoOriginal = btnAdd.textContent;
    btnAdd.textContent = "¡Agregado! 👟";
    btnAdd.classList.add("agregado");
    
    const badge = document.getElementById('contador-carrito');
    badge.classList.add("animar");

    setTimeout(() => {
        btnAdd.textContent = textoOriginal;
        btnAdd.classList.remove("agregado");
        badge.classList.remove("animar");
    }, 1200);
}

function quitarDelCarrito(indexCarrito) {
    carrito.splice(indexCarrito, 1);
    actualizarCarrito();
}

function actualizarCarrito() {
    const lista = document.getElementById('lista-carrito');
    const contador = document.getElementById('contador-carrito');
    const footerOpciones = document.getElementById('footer-opciones');

    lista.innerHTML = '';
    
    let sumaParesZapas = 0;
    let cantRemeraBlanca = 0;
    let cantRemeraNegra = 0;
    let cantBaggyGris = 0;
    let cantBaggyNegro = 0;

    carrito.forEach(item => {
        let m = item.modelo.toLowerCase();
        if (m.includes("remera adidas blanca")) cantRemeraBlanca += item.cantidad;
        else if (m.includes("remera adidas negra")) cantRemeraNegra += item.cantidad;
        else if (m.includes("baggy nk") && m.includes("gris")) cantBaggyGris += item.cantidad;
        else if (m.includes("baggy nk") && m.includes("negro")) cantBaggyNegro += item.cantidad;
        else sumaParesZapas += item.cantidad;
    });

    let calificaMayorista = (sumaParesZapas >= 5);
    let totalUnidad = 0;
    let totalMayor = 0;

    carrito.forEach((item, i) => {
        const prodRef = stock_actualizado.find(p => p.modelo === item.modelo);
        const foto = prodRef ? prodRef.foto : '';
        let m = item.modelo.toLowerCase();

        let precioMin = obtenerPrecioMinorista(item.modelo);
        let subtotalMostrar = 0;
        let subtotalMayor = 0;

        if (m.includes("remera adidas blanca")) {
            let precioRemeraBlanca = (cantRemeraBlanca >= 10) ? 15000 : 20000;
            subtotalMostrar = precioRemeraBlanca * item.cantidad;
            subtotalMayor = subtotalMostrar;
        } else if (m.includes("remera adidas negra")) {
            let precioRemeraNegra = (cantRemeraNegra >= 10) ? 15000 : 20000;
            subtotalMostrar = precioRemeraNegra * item.cantidad;
            subtotalMayor = subtotalMostrar;
        } else if (m.includes("baggy nk") && m.includes("gris")) {
            let precioBaggyGris = (cantBaggyGris >= 10) ? 22000 : 28000;
            subtotalMostrar = precioBaggyGris * item.cantidad;
            subtotalMayor = subtotalMostrar;
        } else if (m.includes("baggy nk") && m.includes("negro")) {
            let precioBaggyNegro = (cantBaggyNegro >= 10) ? 22000 : 28000;
            subtotalMostrar = precioBaggyNegro * item.cantidad;
            subtotalMayor = subtotalMostrar;
        } else {
            subtotalMostrar = precioMin * item.cantidad;
            subtotalMayor = obtenerPrecioMayorista(item.modelo) * item.cantidad;
        }

        totalUnidad += subtotalMostrar;
        totalMayor += subtotalMayor;

        lista.innerHTML += `
            <li class="item-carrito">
                <div style="display:flex; align-items:center; flex:1;">
                    <img src="${foto}" class="cart-thumb" onerror="this.style.display='none'">
                    <div class="item-info">
                        <div style="font-weight:bold; font-size:13px; line-height:1.2; margin-bottom:3px;">${item.modelo}</div>
                        <div style="font-size: 12px; color: #555;">
                            <span class="badge-cant">${item.cantidad}x</span> Talle: ${item.talle} - $${subtotalMostrar.toLocaleString('es-AR')}
                        </div>
                    </div>
                </div>
                <button class="btn-quitar" onclick="quitarDelCarrito(${i})">✖</button>
            </li>
        `;
    });

    let sumaTotalItems = carrito.reduce((acc, item) => acc + item.cantidad, 0);
    contador.textContent = sumaTotalItems;

    if (sumaTotalItems === 0) {
        footerOpciones.innerHTML = `<div style="text-align:center; padding: 20px; color: #666;">Tu carrito está vacío</div>`;
    } else if (calificaMayorista) {
        footerOpciones.innerHTML = `
            <div class="opcion-compra mayorista">
                <div class="detalle-opcion">
                    <strong>Comprando por mayor (5 pares o más)</strong>
                    <span class="precio-final">$${totalMayor.toLocaleString('es-AR')}</span>
                    <span class="aviso-cambio">Sin cambio de talle</span>
                </div>
                <button class="btn-whatsapp" onclick="enviarPedido('mayor')">Pedir por mayor 📲</button>
            </div>
            <div class="opcion-compra minorista">
                <div class="detalle-opcion">
                    <strong>Comprando por unidad</strong>
                    <span class="precio-final">$${totalUnidad.toLocaleString('es-AR')}</span>
                    <span class="aviso-cambio" style="color:#28a745;">Con cambio de talle</span>
                </div>
                <button class="btn-whatsapp outline" onclick="enviarPedido('unidad')">Pedir por unidad 📲</button>
            </div>
        `;
    } else {
        footerOpciones.innerHTML = `
            <div style="text-align:center; margin-bottom: 10px;">
                <span style="font-size:16px; font-weight:bold;">Total: $${totalUnidad.toLocaleString('es-AR')}</span>
            </div>
            <button class="btn-whatsapp" onclick="enviarPedido('unidad')">Pedir por WhatsApp 📲</button>
        `;
    }
}

function abrirCarrito() { document.getElementById('modal-carrito').style.display = 'flex'; }
function cerrarCarrito() { document.getElementById('modal-carrito').style.display = 'none'; }

function enviarPedido(modoElegido) {
    if(carrito.length === 0) return alert("No seleccionaste ningún modelo.");

    let mensaje = "¡Hola! Quiero hacer el siguiente pedido del catálogo:%0A%0A";
    
    let sumaParesZapas = 0;
    let cantRemeraBlanca = 0;
    let cantRemeraNegra = 0;
    let cantBaggyGris = 0;
    let cantBaggyNegro = 0;

    carrito.forEach(item => {
        let m = item.modelo.toLowerCase();
        if (m.includes("remera adidas blanca")) cantRemeraBlanca += item.cantidad;
        else if (m.includes("remera adidas negra")) cantRemeraNegra += item.cantidad;
        else if (m.includes("baggy nk") && m.includes("gris")) cantBaggyGris += item.cantidad;
        else if (m.includes("baggy nk") && m.includes("negro")) cantBaggyNegro += item.cantidad;
        else sumaParesZapas += item.cantidad;
    });

    let calificaMayorista = (sumaParesZapas >= 5);
    let usarMayorista = calificaMayorista && (modoElegido === 'mayor');

    let total = 0;

    carrito.forEach(item => {
        let m = item.modelo.toLowerCase();
        let precioMin = obtenerPrecioMinorista(item.modelo);
        let precio = precioMin;

        if (m.includes("remera adidas blanca")) {
            precio = (cantRemeraBlanca >= 10) ? 15000 : 20000;
        } else if (m.includes("remera adidas negra")) {
            precio = (cantRemeraNegra >= 10) ? 15000 : 20000;
        } else if (m.includes("baggy nk") && m.includes("gris")) {
            precio = (cantBaggyGris >= 10) ? 22000 : 28000;
        } else if (m.includes("baggy nk") && m.includes("negro")) {
            precio = (cantBaggyNegro >= 10) ? 22000 : 28000;
        } else {
            precio = usarMayorista ? obtenerPrecioMayorista(item.modelo) : precioMin;
        }

        let subtotal = precio * item.cantidad;
        total += subtotal;

        mensaje += `${item.modelo} (${item.talle}) $${precio.toLocaleString('es-AR')}`;
        if (item.cantidad > 1) {
            mensaje += `, x${item.cantidad}`;
        }
        mensaje += "%0A";
    });

    mensaje += `%0ATotal: $${total.toLocaleString('es-AR')}%0A`;

    if (calificaMayorista) {
        if (usarMayorista) {
            mensaje += `%0ACompra por MAYOR (5 pares o más): SIN cambio de talle.%0A`;
        } else {
            mensaje += `%0ACompra por UNIDAD: CON posibilidad de cambio de talle.%0A`;
        }
    }

    const url = `https://wa.me/${TU_NUMERO}?text=${mensaje}`;
    window.open(url, '_blank');
}

setTimeout(cargarProductos, 100);