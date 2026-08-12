const TU_NUMERO = "5491153773771"; 
const PRECIO_MINORISTA = 43000;
let carrito = [];

function obtenerPrecioMayorista(nombreProducto) {
    const nombre = nombreProducto.toLowerCase();
    
    if (nombre.includes("air force exclusivas white")) return 41000;
    if (nombre.includes("vans haylan")) return 42000;
    if (nombre.includes("dunk pombo") || nombre.includes("glistter") || nombre.includes("glitter") || nombre.includes("dunk total black") || nombre.includes("combinada celeste")) return 37000;
    if (nombre.includes("botitas charol") && nombre.includes("jordan")) return 39000;
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
                        <div style="font-weight:bold; font-size:13px;">${item.modelo}</div>
                        <div style="font-size: 12px; color: #555;">${item.cantidad}x Talle: ${item.talle} | $${subtotalMostrar.toLocaleString('es-AR')}</div>
                    </div>
                </div>
                <button class="btn-quitar" onclick="quitarDelCarrito(${i})">✖</button>
            </li>`;
    });

    contador.textContent = sumaPares;

    if (sumaPares === 0) {
        footerOpciones.innerHTML = `<div style="text-align:center; padding: 20px; color: #666;">Carrito vacío</div>`;
    } else if (sumaPares < 5) {
        footerOpciones.innerHTML = `
            <div style="text-align:center; margin-bottom:10px;">
                <p>Total: <strong>$${totalPrecioMinorista.toLocaleString('es-AR')}</strong></p>
                <small style="color:#d9534f;">Faltan ${5 - sumaPares} para precio mayorista</small>
            </div>
            <button class="btn-whatsapp" onclick="enviarPedido(false)">Pedir por WhatsApp 📲</button>`;
    } else {
        footerOpciones.innerHTML = `
            <div class="opcion-compra minorista">
                <strong>Minorista (Con Cambio)</strong>
                <span class="precio-final">$${totalPrecioMinorista.toLocaleString('es-AR')}</span>
                <button class="btn-whatsapp outline" onclick="enviarPedido(false)">Pedir Minorista</button>
            </div>
            <div class="opcion-compra mayorista">
                <strong>Mayorista</strong>
                <span class="precio-final">$${totalPrecioMayorista.toLocaleString('es-AR')}</span>
                <span class="aviso-cambio">⚠️ SIN CAMBIO DE TALLE</span>
                <button class="btn-whatsapp" onclick="enviarPedido(true)">Pedir Mayorista 📲</button>
            </div>`;
    }
}

function enviarPedido(esMayorista) {
    let mensaje = "🚀 *NUEVO PEDIDO DE TIENDA*%0A%0A";
    mensaje += esMayorista ? "🚨 *MODALIDAD: MAYORISTA* (Sin cambios)%0A" : "🛍️ *MODALIDAD: MINORISTA* (Con cambios)%0A";
    mensaje += "---------------------------%0A";
    
    let total = 0;
    carrito.forEach(item => {
        let precio = esMayorista ? obtenerPrecioMayorista(item.modelo) : PRECIO_MINORISTA;
        total += (precio * item.cantidad);
        mensaje += `👟 *${item.modelo}*%0A👉 ${item.cantidad} par/es | Talle ${item.talle} | $${precio.toLocaleString('es-AR')} c/u%0A%0A`;
    });

    mensaje += "---------------------------%0A";
    mensaje += `💰 *TOTAL A PAGAR: $${total.toLocaleString('es-AR')}*`;

    window.open(`https://wa.me/${TU_NUMERO}?text=${mensaje}`, '_blank');
}

// (CargarProductos, filtrar y otros métodos van aquí abajo...)
setTimeout(cargarProductos, 100);