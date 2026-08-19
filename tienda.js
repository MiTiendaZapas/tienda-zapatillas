const TU_NUMERO = "5491153773771"; 
let carrito = [];

function obtenerPrecioMinorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();

    // EXCEPCIÓN DE OJOTAS LOUIS VUITTON NEGRAS ($35.000 por unidad)
    if (nombre.includes("ojotas louis vuitton negras") || nombre.includes("louis vuitton negras")) {
        return 35000;
    }

    // EXCEPCIÓN DE NIÑO POR UNIDAD ($35.000)
    if (nombre.includes("niño") || nombre.includes("niños")) {
        return 35000;
    }

    // Excepciones de $55.000 por unidad
    if (nombre.includes("jordan 11 suela azul") ||
        nombre.includes("jordan 11 negra/blanca") ||
        nombre.includes("jordan 11 negra blanca")) {
        return 55000;
    }

    // Precio por defecto por unidad para el resto del catálogo
    return 43000; 
}

function obtenerPrecioMayorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();

    // 1. EXCEPCIONES MUY ESPECÍFICAS (Se leen primero para no chocar con las categorías generales)
    if (nombre.includes("ojotas louis vuitton negras") || nombre.includes("louis vuitton negras")) {
        return 31000;
    }

    if (nombre.includes("botitas jordan niño") || nombre.includes("niño") || nombre.includes("niños")) {
        return 30000;
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
        nombre.includes("jordan 1 brillosa") || 
        nombre.includes("super star brillo") ||
        nombre.includes("súper star brillo") ||
        nombre.includes("super star brillo perla") ||
        nombre.includes("súper star brillo perla") ||
        nombre.includes("adidas 2000") || 
        nombre.includes("puma 180") || 
        nombre.includes("shox") ||
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

function cargarProductos() {
    const grid = document.getElementById('grid-productos');
    grid.innerHTML = '';

    if (typeof stock_actualizado === 'undefined') {
        grid.innerHTML = '<h3 style="color:red;">Error: No se encontró el catálogo.</h3>';
        return;
    }

    stock_actualizado.forEach((producto, index) => {
        if(!producto.talles || producto.talles.length === 0) return;

        let botonesTalles = producto.talles.map(t => {
            let numeroTalle = t.talle !== undefined ? t.talle : t;
            let cantidadStock = t.stock !== undefined ? t.stock : 99;
            let sinStockClass = cantidadStock <= 0 ? 'disabled' : '';
            let disabledAttr = cantidadStock <= 0 ? 'disabled' : '';

            return `<button type="button" class="talle-cuadro ${sinStockClass}" data-talle="${numeroTalle}" data-stock="${cantidadStock}" ${disabledAttr} onclick="seleccionarTalle(${index}, '${numeroTalle}', ${cantidadStock}, this)">${numeroTalle}</button>`;
        }).join('');

        let precioMinorista = obtenerPrecioMinorista(producto.modelo);
        let precioMayorista = obtenerPrecioMayorista(producto.modelo);

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
                    <div style="font-size: 12px; color: #28a745; margin-bottom: 6px; font-weight: bold;">
                        Llevando 5 o más: $${precioMayorista.toLocaleString('es-AR')}
                    </div>
                    
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
    const talleNumero = isNaN(talleElegido) ? talleElegido : parseInt(talleElegido);
    
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
        return a.talle - b.talle;
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
    let sumaPares = 0;
    let totalPrecioMinorista = 0;
    let totalPrecioMayorista = 0;

    carrito.forEach(item => { sumaPares += item.cantidad; });
    let esMayorista = (sumaPares >= 5);

    carrito.forEach((item, i) => {
        const prodRef = stock_actualizado.find(p => p.modelo === item.modelo);
        const foto = prodRef ? prodRef.foto : '';

        let precioMin = obtenerPrecioMinorista(item.modelo);
        let precioMay = obtenerPrecioMayorista(item.modelo);

        totalPrecioMinorista += precioMin * item.cantidad;
        totalPrecioMayorista += precioMay * item.cantidad;

        let subtotalMostrar = (esMayorista ? precioMay : precioMin) * item.cantidad;

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

    contador.textContent = sumaPares;

    if (sumaPares === 0) {
        footerOpciones.innerHTML = `<div style="text-align:center; padding: 20px; color: #666;">Tu carrito está vacío</div>`;
    } else if (sumaPares < 5) {
        footerOpciones.innerHTML = `
            <div style="text-align:center; margin-bottom: 10px;">
                <span style="font-size:16px; font-weight:bold;">Total: $${totalPrecioMinorista.toLocaleString('es-AR')}</span>
                <div style="font-size:12px; color:#d9534f; margin-top:5px;">Agregá ${5 - sumaPares} par(es) más para acceder a precio mayorista.</div>
            </div>
            <button class="btn-whatsapp" onclick="enviarPedido(false)">Pedir por WhatsApp 📲</button>
        `;
    } else {
        footerOpciones.innerHTML = `
            <div style="text-align:center; margin-bottom:10px;">
                <span style="font-size:13px; color:#666;">¡Llegaste a los 5 pares! Elegí tu plan:</span>
            </div>
            
            <div class="opcion-compra minorista">
                <div class="detalle-opcion">
                    <strong>Comprar Minorista (Con Cambio)</strong>
                    <span class="precio-final">$${totalPrecioMinorista.toLocaleString('es-AR')}</span>
                </div>
                <button class="btn-whatsapp outline" onclick="enviarPedido(false)">Elegir Minorista</button>
            </div>

            <div class="opcion-compra mayorista">
                <div class="detalle-opcion">
                    <strong>Comprar Mayorista</strong>
                    <span class="precio-final">$${totalPrecioMayorista.toLocaleString('es-AR')}</span>
                    <span class="aviso-cambio">⚠️ SIN CAMBIO DE TALLE</span>
                </div>
                <button class="btn-whatsapp" onclick="enviarPedido(true)">Elegir Mayorista 📲</button>
            </div>
        `;
    }
}

function abrirCarrito() { document.getElementById('modal-carrito').style.display = 'flex'; }
function cerrarCarrito() { document.getElementById('modal-carrito').style.display = 'none'; }

function enviarPedido(esMayorista) {
    if(carrito.length === 0) return alert("No seleccionaste ningún modelo.");

    let mensaje = "¡Hola! Quiero hacer el siguiente pedido del catálogo:%0A%0A";
    
    let total = 0;
    carrito.forEach(item => {
        let precio = esMayorista ? obtenerPrecioMayorista(item.modelo) : obtenerPrecioMinorista(item.modelo);
        let subtotal = precio * item.cantidad;
        total += subtotal;

        mensaje += `${item.modelo} (${item.talle}) $${precio.toLocaleString('es-AR')}`;
        if (item.cantidad > 1) {
            mensaje += `, x${item.cantidad}`;
        }
        mensaje += "%0A";
    });

    mensaje += `%0ATotal: $${total.toLocaleString('es-AR')}%0A`;
    
    if (esMayorista) {
        mensaje += "Compra mayorista sin cambio";
    } else {
        mensaje += "Compra minorista con cambio";
    }

    const url = `https://wa.me/${TU_NUMERO}?text=${mensaje}`;
    window.open(url, '_blank');
}

setTimeout(cargarProductos, 100);