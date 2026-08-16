const TU_NUMERO = "5491153773771"; 
let carrito = [];

function obtenerPrecioMinorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();

    // PRECIOS MINORISTAS (Basados en tu tabla para 2 unidades o menos)
    if (nombre.includes("adidas 2000") || nombre.includes("air forcé con medias") || nombre.includes("air force con medias") || nombre.includes("puma 180") || nombre.includes("shox") || nombre.includes("haylan") || nombre.includes("vans haylan")) return 60000;
    
    if (nombre.includes("retro 4") || nombre.includes("retro 1") || nombre.includes("botitas") || nombre.includes("jordan") || nombre.includes("530") || nombre.includes("9060") || nombre.includes("abzorb") || nombre.includes("running") || nombre.includes("mind") || nombre.includes("new balance")) return 55000;
    
    // Por defecto para el resto (Dunk, Forum, Vans, Fila, Air Force, Super Star, Puma, etc.)
    return 50000; 
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

        let precioUnitario = obtenerPrecioMinorista(producto.modelo);

        grid.innerHTML += `
            <div class="producto-card" data-modelo="${producto.modelo.toLowerCase()}">
                <div class="img-container">
                    <img src="${producto.foto}" alt="${producto.modelo}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="sin-foto">📸<br>Falta Imagen</div>
                </div>
                <div class="info-prod">
                    <div>
                        <div class="titulo">${producto.modelo}</div>
                        <div style="font-size: 20px; font-weight: bold; color: #111; margin-top: 2px; margin-bottom: 12px;">
                            $${precioUnitario.toLocaleString('es-AR')}
                        </div>
                        
                        <div class="talles-grid-container" id="talles-container-${index}">
                            ${botonesTalles}
                        </div>
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
    let precioTotal = 0;

    carrito.forEach(item => { sumaPares += item.cantidad; });

    carrito.forEach((item, i) => {
        const prodRef = stock_actualizado.find(p => p.modelo === item.modelo);
        const foto = prodRef ? prodRef.foto : '';
        const precioUnitario = obtenerPrecioMinorista(item.modelo);
        let subtotal = precioUnitario * item.cantidad;
        precioTotal += subtotal;

        lista.innerHTML += `
            <li class="item-carrito">
                <div style="display:flex; align-items:center; flex:1;">
                    <img src="${foto}" class="cart-thumb" onerror="this.style.display='none'">
                    <div class="item-info">
                        <div style="font-weight:bold; font-size:13px; line-height:1.2; margin-bottom:3px;">${item.modelo}</div>
                        <div style="font-size: 12px; color: #555;">
                            <span class="badge-cant">${item.cantidad}x</span> Talle: ${item.talle} - $${subtotal.toLocaleString('es-AR')}
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
    } else {
        footerOpciones.innerHTML = `
            <div style="text-align:center; margin-bottom: 12px;">
                <span style="font-size:16px; font-weight:bold;">Total: $${precioTotal.toLocaleString('es-AR')}</span>
            </div>
            <button class="btn-whatsapp" onclick="enviarPedido()">Pedir por WhatsApp 📲</button>
        `;
    }
}

function abrirCarrito() { document.getElementById('modal-carrito').style.display = 'flex'; }
function cerrarCarrito() { document.getElementById('modal-carrito').style.display = 'none'; }

function enviarPedido() {
    if(carrito.length === 0) return alert("No seleccionaste ningún modelo.");

    let mensaje = "¡Hola! Quiero hacer el siguiente pedido minorista:%0A%0A";
    let total = 0;

    carrito.forEach(item => {
        let precio = obtenerPrecioMinorista(item.modelo);
        let subtotal = precio * item.cantidad;
        total += subtotal;

        mensaje += `${item.modelo} (${item.talle}) $${precio.toLocaleString('es-AR')}`;
        if (item.cantidad > 1) {
            mensaje += `, x${item.cantidad}`;
        }
        mensaje += "%0A";
    });

    mensaje += `%0ATotal: $${total.toLocaleString('es-AR')}`;

    const url = `https://wa.me/${TU_NUMERO}?text=${mensaje}`;
    window.open(url, '_blank');
}

setTimeout(cargarProductos, 100);