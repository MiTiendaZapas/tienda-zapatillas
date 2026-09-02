// ============================================================
// Panel Admin - lógica de frontend (vanilla JS, sin frameworks)
// ============================================================

// ---------- Navegación por pestañas ----------
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => cambiarTab(btn.dataset.tab));
});

function cambiarTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('activa', b.dataset.tab === tab));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('activa', p.id === `tab-${tab}`));

    if (tab === 'dashboard') cargarDashboard();
    if (tab === 'zapatillas') cargarStock('zapatillas');
    if (tab === 'indumentaria') cargarStock('indumentaria');
}

// ============================================================
// DASHBOARD
// ============================================================

async function cargarDashboard() {
    const resp = await fetch('/api/dashboard');
    const data = await resp.json();

    document.getElementById('total-catalogo').textContent = data.total_catalogo;
    document.getElementById('total-faltantes').textContent = data.cantidad_faltan;

    const contenedor = document.getElementById('lista-faltantes');
    contenedor.innerHTML = '';

    if (data.faltan_foto.length === 0) {
        contenedor.innerHTML = '<div class="sin-faltantes">✅ Todos los modelos del proveedor tienen foto.</div>';
        return;
    }

    data.faltan_foto.forEach(modelo => {
        const fila = document.createElement('div');
        fila.className = 'fila-faltante';
        const idInput = `foto-falt-${btoa(unescape(encodeURIComponent(modelo))).replace(/[^a-zA-Z0-9]/g, '')}`;
        fila.innerHTML = `
            <span class="nombre">${escapeHtml(modelo)}</span>
            <input type="file" id="${idInput}" accept=".jpg,.jpeg,.png,.webp">
            <button class="btn btn-primario btn-chico" data-modelo="${escapeHtml(modelo)}" data-input="${idInput}">Subir foto</button>
        `;
        fila.querySelector('button').addEventListener('click', (e) => {
            const modeloBtn = e.target.dataset.modelo;
            const inputEl = document.getElementById(e.target.dataset.input);
            subirFotoFaltante(modeloBtn, inputEl, fila);
        });
        contenedor.appendChild(fila);
    });
}

// El piloto automático corre aparte (acceso directo propio) y va
// reescribiendo catalogo.js solo, cada 14-18 min. Mientras estés en la
// pestaña Inicio, refrescamos el dashboard cada 20s para reflejar eso
// sin que tengas que ir cambiando de pestaña para forzar la recarga.
setInterval(() => {
    if (document.getElementById('tab-dashboard').classList.contains('activa')) {
        cargarDashboard();
    }
}, 20000);

async function subirFotoFaltante(modelo, inputEl, filaEl) {
    if (!inputEl.files || inputEl.files.length === 0) {
        alert('Elegí un archivo primero.');
        return;
    }
    const form = new FormData();
    form.append('modelo', modelo);
    form.append('foto', inputEl.files[0]);

    const resp = await fetch('/api/upload-foto', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.error) {
        alert('Error: ' + data.error);
        return;
    }
    filaEl.style.opacity = '0.4';
    filaEl.innerHTML = `<span class="nombre">✅ ${escapeHtml(modelo)} - foto subida</span>`;
    setTimeout(cargarDashboard, 800);
}

// ============================================================
// STOCK MANUAL (zapatillas / indumentaria)
// ============================================================

async function cargarStock(tipo) {
    const resp = await fetch(`/api/stock/${tipo}`);
    const productos = await resp.json();
    const contenedor = document.getElementById(`tabla-${tipo}`);
    contenedor.innerHTML = '';

    if (productos.length === 0) {
        contenedor.innerHTML = '<div class="sin-faltantes">No hay modelos cargados todavía.</div>';
        return;
    }

    productos.sort((a, b) => a.modelo.localeCompare(b.modelo));

    productos.forEach(p => {
        const resumenTalles = p.talles.map(t => `${t.talle}:${t.stock}`).join(' · ');
        const fila = document.createElement('div');
        fila.className = 'fila-stock';
        fila.innerHTML = `
            <img class="thumb" src="/${p.foto}" onerror="this.style.visibility='hidden'">
            <div class="info">
                <div class="nombre">${escapeHtml(p.modelo)} ${p.tiene_foto ? '' : '<span class="badge-sin-foto">sin foto</span>'}</div>
                <div class="talles-resumen">${escapeHtml(resumenTalles)}</div>
            </div>
            <div class="acciones">
                <button class="btn btn-chico">Editar</button>
                <button class="btn btn-borrar btn-chico">Borrar</button>
            </div>
        `;
        const [btnEditar, btnBorrar] = fila.querySelectorAll('button');
        btnEditar.addEventListener('click', () => abrirFormulario(tipo, p));
        btnBorrar.addEventListener('click', () => borrarProducto(tipo, p.modelo));
        contenedor.appendChild(fila);
    });
}

async function borrarProducto(tipo, modelo) {
    if (!confirm(`¿Borrar "${modelo}" del stock manual? Esto no borra la foto.`)) return;
    const resp = await fetch(`/api/stock/${tipo}/${encodeURIComponent(modelo)}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.error) {
        alert('Error: ' + data.error);
        return;
    }
    cargarStock(tipo);
}

// ---------- Modal: agregar / editar producto ----------

let fotoArchivoSeleccionado = null;

function abrirFormulario(tipo, producto) {
    document.getElementById('f-tipo').value = tipo;
    document.getElementById('form-error').textContent = '';
    fotoArchivoSeleccionado = null;

    const preview = document.getElementById('f-foto-preview');
    const actual = document.getElementById('f-foto-actual');
    const inputArchivo = document.getElementById('f-foto-archivo');
    inputArchivo.value = '';

    document.getElementById('f-talles-filas').innerHTML = '';

    if (producto) {
        document.getElementById('modal-titulo').textContent = 'Editar modelo';
        document.getElementById('f-modelo-original').value = producto.modelo;
        document.getElementById('f-modelo').value = producto.modelo;
        preview.src = '/' + producto.foto;
        preview.style.display = 'inline-block';
        actual.textContent = 'Foto actual: ' + producto.foto;
        producto.talles.forEach(t => agregarFilaTalle(t.talle, t.stock));
    } else {
        document.getElementById('modal-titulo').textContent = 'Agregar modelo';
        document.getElementById('f-modelo-original').value = '';
        document.getElementById('f-modelo').value = '';
        preview.style.display = 'none';
        actual.textContent = tipo === 'indumentaria'
            ? 'Talles sugeridos: S, M, L, XL, XXL'
            : 'Se calcula sola a partir del nombre del modelo.';
        agregarFilaTalle();
    }

    inputArchivo.onchange = () => {
        fotoArchivoSeleccionado = inputArchivo.files[0] || null;
        if (fotoArchivoSeleccionado) {
            preview.src = URL.createObjectURL(fotoArchivoSeleccionado);
            preview.style.display = 'inline-block';
        }
    };

    document.getElementById('modal-form').classList.add('activa');
}

function cerrarFormulario() {
    document.getElementById('modal-form').classList.remove('activa');
}

function agregarFilaTalle(talle, stock) {
    const contenedor = document.getElementById('f-talles-filas');
    const fila = document.createElement('div');
    fila.className = 'fila-talle';
    fila.innerHTML = `
        <input type="text" class="f-talle" placeholder="Talle (ej: 40 o M)" value="${talle !== undefined ? escapeHtml(String(talle)) : ''}">
        <input type="number" class="f-stock" placeholder="Stock" min="0" value="${stock !== undefined ? stock : ''}">
        <button type="button" onclick="this.parentElement.remove()">✖</button>
    `;
    contenedor.appendChild(fila);
}

async function guardarProducto(evento) {
    evento.preventDefault();
    const tipo = document.getElementById('f-tipo').value;
    const modeloOriginal = document.getElementById('f-modelo-original').value;
    const modelo = document.getElementById('f-modelo').value.trim();
    const errorEl = document.getElementById('form-error');
    errorEl.textContent = '';

    const talles = [];
    document.querySelectorAll('#f-talles-filas .fila-talle').forEach(fila => {
        const talleTexto = fila.querySelector('.f-talle').value.trim();
        const stockTexto = fila.querySelector('.f-stock').value.trim();
        if (!talleTexto || stockTexto === '') return;
        const talleValor = /^\d+$/.test(talleTexto) ? parseInt(talleTexto, 10) : talleTexto;
        talles.push({ talle: talleValor, stock: parseInt(stockTexto, 10) });
    });

    if (!modelo) {
        errorEl.textContent = 'Falta el nombre del modelo.';
        return false;
    }
    if (talles.length === 0) {
        errorEl.textContent = 'Agregá al menos un talle con stock.';
        return false;
    }

    // 1) Si eligió una foto nueva, subirla primero
    let rutaFoto = null;
    if (fotoArchivoSeleccionado) {
        const form = new FormData();
        form.append('modelo', modelo);
        form.append('foto', fotoArchivoSeleccionado);
        const respFoto = await fetch('/api/upload-foto', { method: 'POST', body: form });
        const dataFoto = await respFoto.json();
        if (dataFoto.error) {
            errorEl.textContent = 'Error subiendo la foto: ' + dataFoto.error;
            return false;
        }
        rutaFoto = dataFoto.foto;
    }

    // 2) Guardar el producto
    const resp = await fetch(`/api/stock/${tipo}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            modelo_original: modeloOriginal,
            modelo,
            talles,
            foto: rutaFoto,
        }),
    });
    const data = await resp.json();
    if (data.error) {
        errorEl.textContent = data.error;
        return false;
    }

    cerrarFormulario();
    cargarStock(tipo);
    return false;
}

// ============================================================
// PUBLICAR (git)
// ============================================================

async function verEstadoGit() {
    const contenedor = document.getElementById('git-status');
    contenedor.textContent = 'Revisando...';
    const resp = await fetch('/api/git/status');
    const data = await resp.json();
    if (data.error) {
        contenedor.textContent = 'Error: ' + data.error;
        return;
    }
    contenedor.textContent = data.cambios.length > 0
        ? data.cambios.join('\n')
        : 'No hay cambios pendientes.';
}

async function publicarCambios() {
    const resultado = document.getElementById('git-resultado');
    resultado.className = 'git-resultado';
    resultado.textContent = 'Publicando, esperá un momento...';
    resultado.style.display = 'block';

    const resp = await fetch('/api/git/publicar', { method: 'POST' });
    const data = await resp.json();

    if (data.ok) {
        resultado.className = 'git-resultado ok';
        resultado.textContent = '✅ ' + data.mensaje;
        verEstadoGit();
    } else {
        resultado.className = 'git-resultado error';
        resultado.textContent = '❌ ' + (data.error || 'Error desconocido');
    }
}

// ---------- utilidades ----------
function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ---------- carga inicial ----------
cargarDashboard();
