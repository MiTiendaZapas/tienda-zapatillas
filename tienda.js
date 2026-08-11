const TU_NUMERO = "5491100000000"; 
const PRECIO_MINORISTA = 43000;
let carrito = [];

function obtenerPrecioMayorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();
    
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
    if (nombre.includes("haylan luxo") || nombre.includes("haylan 01 luxo")) return 42000;
    
    return PRECIO_MINORISTA; 
}

function cargarProductos() {
    const grid = document.getElementById('grid-productos');
    grid.innerHTML = '';

    if (typeof stock_actualizado === 'undefined') {
        grid.innerHTML = '<h3 style="color:red;">Error: No se encontró el catálogo. Asegurate de correr el piloto_automatico.py</h3>';
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
    const talleElegido = opcionSeleccionada.value;
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

    actualizarCarrito();

    // CONFIRMACIÓN VISUAL SIN ABRIR EL CARRITO
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
    const resumenCant = document.getElementById('resumen-cantidad');
    const resumenTotal = document.getElementById('resumen-total');
    const badgeTipo = document.getElementById('badge-tipo-compra');

    lista.innerHTML = '';
    let sumaPares = 0;
    let totalPrecio = 0;

    carrito.forEach(item => {
        sumaPares += item.cantidad;
    });

    let esMayorista = (sumaPares >= 5);

    carrito.forEach((item, i) => {
        let precioUnitario = esMayorista ? obtenerPrecioMayorista(item.modelo) : PRECIO_MINORISTA;
        let subtotal = precioUnitario * item.cantidad;
        totalPrecio += subtotal;

        lista.innerHTML += `
            <li class="item-carrito">
                <div class="item-info">
                    <div>👟 ${item.modelo}</div>
                    <div style="font-size: 13px; font-weight: bold; color: #111;">
                        <span class="badge-cant">${item.cantidad}x</span> Talle: ${item.talle} - $${subtotal.toLocaleString('es-AR')}
                    </div>
                </div>
                <button class="btn-quitar" onclick="quitarDelCarrito(${i})">✖</button>
            </li>
        `;
    });

    contador.textContent = sumaPares;
    resumenCant.textContent = `${sumaPares} pares en total`;
    resumenTotal.textContent = `$${totalPrecio.toLocaleString('es-AR')}`;

    if (sumaPares === 0) {
        badgeTipo.textContent = "";
    } else if (esMayorista) {
        badgeTipo.textContent = "🔥 ¡PRECIO MAYORISTA APLICADO! (Sin cambio de talle)";
        badgeTipo.style.color = "#28a745";
    } else {
        badgeTipo.textContent = `Pagas minorista. Agregá ${5 - sumaPares} par(es) más para precio mayorista.`;
        badgeTipo.style.color = "#d9534f";
    }
}

function abrirCarrito() { document.getElementById('modal-carrito').style.display = 'flex'; }
function cerrarCarrito() { document.getElementById('modal-carrito').style.display = 'none'; }

function enviarPedido() {
    if(carrito.length === 0) return alert("No seleccionaste ningún modelo.");

    let cantidadTotalPares = 0;
    carrito.forEach(item => {
        cantidadTotalPares += item.cantidad;
    });

    let esMayorista = false;

    if (cantidadTotalPares >= 5) {
        let mensajeAlerta = "¡Llevás 5 pares o más! 🎉\n\nPodés acceder a nuestro precio MAYORISTA.\n⚠️ ATENCIÓN: Las compras por mayor NO tienen cambio de talle.\n\n¿Querés comprar por mayor sin cambio de talle (Aceptar) o mantener el precio unitario con cambio (Cancelar)?";
        esMayorista = confirm(mensajeAlerta);
    }

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