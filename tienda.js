// ⚠️ ACORDATE DE PONER TU NÚMERO DE TELÉFONO ACÁ ⚠️
const TU_NUMERO = "5491100000000"; 
const PRECIO_MINORISTA = 43000;
let carrito = [];

function obtenerPrecioMayorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();
    
    // -- TUS PRECIOS NUEVOS ACTUALIZADOS --
    if (nombre.includes("air force exclusivas white") || nombre.includes("air forcé exclusivas white")) return 41000;
    if (nombre.includes("vans haylan")) return 42000; // Esto ya cubre 01, nova, black, beige, bonitas, azul, grafite, marron, luxo
    if (nombre.includes("dunk pombo") || nombre.includes("glistter") || nombre.includes("glitter") || nombre.includes("dunk total black") || nombre.includes("combinada celeste")) return 37000;
    if (nombre.includes("botitas charol") && nombre.includes("jordan")) return 39000;

    // -- RESTO DEL DICCIONARIO --
    if (nombre.includes("sb dunk")) return 37000;
    if (nombre.includes("adidas forum") || nombre.includes("adidas fórum")) return 37000;
    if (nombre.includes("adidas 2000")) return 41000;
    if (nombre.includes("vans clásicas") || nombre.includes("vans knu")) return 37000;
    if (nombre.includes("retro 4")) return 39000;
    if (nombre.includes("retro 1") || nombre.includes("jordan 1") || nombre.includes("botitas jordan")) return 39000;
    if (nombre.includes("deportivas fit")) return 37000;
    if (nombre.includes("fila")) return 37000;
    if (nombre.includes("air forcé con medias") || nombre.includes("air force con medias") || nombre.includes("negras medias")) return 41000;
    if (nombre.includes("air force") || nombre.includes("air forcé")) return 37000;
    if (nombre.includes("super star") || nombre.includes("súper star") || nombre.includes("samba")) return 37000;
    if (nombre.includes("abzorb")) return 39000;
    if (nombre.includes("9060")) return 39000;
    if (nombre.includes("running")) return 39000;
    if (nombre.includes("nova")) return 39000;
    if (nombre.includes("puma 180")) return 42000;
    if (nombre.includes("shox")) return 42000;
    if (nombre.includes("puma bmw")) return 37000;
    if (nombre.includes("jordan low")) return 39000;
    
    return PRECIO_MINORISTA; 
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

        let opcionesTalles = producto.talles.map(t => {
            let numeroTalle = t.talle !== undefined ? t.talle : t;
            let cantidadStock = t.stock !== undefined ? t.stock : 99;
            return `<option value="${numeroTalle}" data-stock="${cantidadStock}">Talle ${numeroTalle}</option>`;
        }).join('');

        let precioMayorista = obtenerPrecioMayorista(producto.modelo);

        grid.innerHTML += `
            <div class="producto-card" data-modelo="${producto.modelo.toLowerCase()}">
                <div class="img-container">
                    <img src="${producto.foto}" alt="${producto.modelo}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="sin-foto">📸<br>Falta Imagen</div>
                </div>
                <div class="info-prod">
                    <div class="titulo">${producto.modelo}</div>
                    
                    <div style="font-size: 20px; font-weight: bold; color: #111; margin-bottom: 2px;">
                        $${PRECIO_MINORISTA.toLocaleString('es-AR')}
                    </div>
                    <div style="font-size: 12px; color: #28a745; margin-bottom: 15px; font-weight: bold;">
                        Llevando 5 o más: $${precioMayorista.toLocaleString('es-AR')}
                    </div>
                    
                    <select id="select-${index}" onchange="actualizarUIStock(${index})">
                        <option value="" disabled selected>Elegí tu talle...</option>
                        ${opcionesTalles}
                    </select>
                    
                    <div class="fila-cantidad">
                        <div class="control-cant">
                            <button class="btn-qty" onclick="cambiarCantidad(${index}, -1)" id="btn-menos-${index}" disabled>-</button>
                            <span class="num-qty" id="cant-${index}">1</span>
                            <button class="btn-qty" onclick="cambiarCantidad(${index}, 1)" id="btn-mas-${index}" disabled>+</button>
                        </div>
                        <span id="label-stock-${index}" class="stock-disponible"></span>
                    </div>

                    <button id="btn-${index}" class="add-btn" onclick="agregarAlCarrito(${index})" disabled>Seleccionar Talle</button>
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

function actualizarUIStock(index) {
    const select = document.getElementById(`select-${index}`);
    const labelStock = document.getElementById(`label-stock-${index}`);
    const btn = document.getElementById(`btn-${index}`);
    const btnMenos = document.getElementById(`btn-menos-${index}`);
    const btnMas = document.getElementById(`btn-mas-${index}`);
    const displayCant = document.getElementById(`cant-${index}`);
    
    const opcionSeleccionada = select.options[select.selectedIndex];
    const stockMax = parseInt(opcionSeleccionada.getAttribute('data-stock'));

    displayCant.textContent = "1";
    btnMenos.disabled = true; 
    btnMas.disabled = (stockMax <= 1);
    
    btn.disabled = false;
    btn.textContent = "Agregar al Pedido";

    if (stockMax >= 99) {
        labelStock.textContent = "¡Stock Disponible!";
        labelStock.className = "stock-disponible sobra";
    } else {
        labelStock.textContent = `Quedan ${stockMax} pares`;
        labelStock.className = "stock-disponible";
    }
}

function cambiarCantidad(index, cambio) {
    const select = document.getElementById(`select-${index}`);
    const opcionSeleccionada = select.options[select.selectedIndex];
    const stockMax = parseInt(opcionSeleccionada.getAttribute('data-stock'));
    
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
    const select = document.getElementById(`select-${indexProd}`);
    const opcionSeleccionada = select.options[select.selectedIndex];
    const talleElegido = parseInt(opcionSeleccionada.value); // Lo pasamos a número para ordenarlo bien
    const stockMax = parseInt(opcionSeleccionada.getAttribute('data-stock'));
    const cantidadDeseada = parseInt(document.getElementById(`cant-${indexProd}`).textContent);

    const prod = stock_actualizado[indexProd];
    const itemExistente = carrito.find(item => item.modelo === prod.modelo && item.talle === talleElegido);
    
    if (itemExistente) {
        if (itemExistente.cantidad + cantidadDeseada > stockMax) {
            alert(`Solo hay ${stockMax} pares de este talle. Ya tenés ${itemExistente.cantidad} en tu pedido.`);
            return;
        }
        itemExistente.cantidad += cantidadDeseada;
    } else {
        carrito.push({
            modelo: prod.modelo,
            talle: talleElegido,
            cantidad: cantidadDeseada
        });
    }

    // 1. ORDENAMOS EL CARRITO: Primero por modelo (A-Z), después por talle (Menor a Mayor)
    carrito.sort((a, b) => {
        if (a.modelo < b.modelo) return -1;
        if (a.modelo > b.modelo) return 1;
        return a.talle - b.talle;
    });

    actualizarCarrito();

    // CONFIRMACIÓN VISUAL SILENCIOSA
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
        // Buscamos la foto original del modelo
        const prodRef = stock_actualizado.find(p => p.modelo === item.modelo);
        const foto = prodRef ? prodRef.foto : '';

        let precioMin = PRECIO_MINORISTA;
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

    // LÓGICA DEL FOOTER CON OPCIONES
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

// Ahora la función recibe directamente si tocó el botón minorista o mayorista
function enviarPedido(esMayorista) {
    if(carrito.length === 0) return alert("No seleccionaste ningún modelo.");

    let mensaje = "¡Hola! Quiero hacer el siguiente pedido del catálogo:%0A%0A";
    let total = 0;

    if (esMayorista) {
        mensaje += "🚨 *TIPO DE COMPRA: MAYORISTA* 🚨%0A(El cliente aceptó que NO hay cambio de talle)%0A%0A";
    } else {
        mensaje += "🛍️ *TIPO DE COMPRA: MINORISTA* 🛍️%0A(Con derecho a cambio de talle)%0A%0A";
    }

    carrito.forEach(item => {
        let precio = esMayorista ? obtenerPrecioMayorista(item.modelo) : PRECIO_MINORISTA;
        let subtotal = precio * item.cantidad;
        total += subtotal;

        mensaje += `👟 *${item.modelo}*%0A`;
        mensaje += `👉 ${item.cantidad} pares - Talle: ${item.talle} - $${precio.toLocaleString('es-AR')} c/u%0A%0A`;
    });

    mensaje += `*TOTAL A PAGAR: $${total.toLocaleString('es-AR')}*`;

    const url = `https://wa.me/${TU_NUMERO}?text=${mensaje}`;
    window.open(url, '_blank');
}

setTimeout(cargarProductos, 100);