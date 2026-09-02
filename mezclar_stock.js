// Combina en un solo producto los talles de un mismo modelo que aparece
// repetido en más de un archivo de stock (por ejemplo: el proveedor tiene
// unos talles en catalogo.js, y vos agregaste más talles del mismo modelo
// a mano en zapatillas_manual.js -> se muestran juntos, como un solo
// producto con todos los talles sumados).
//
// La comparación de "es el mismo modelo" es por nombre exacto, sin
// importar mayúsculas/minúsculas ni espacios de más al principio/final.
// Por eso, para que dos entradas se fusionen, el nombre tiene que estar
// escrito IGUAL en los dos lugares (ej: "Nike super star" en catalogo.js
// y "Nike super star" en zapatillas_manual.js). Si hay una letra de
// diferencia, el sistema los va a tratar como dos productos distintos.
function mezclarStockPorModelo(listaProductos) {
    const mapa = new Map();
    const orden = [];

    listaProductos.forEach(producto => {
        if (!producto || !producto.modelo) return;
        const clave = producto.modelo.toLowerCase().trim();

        if (!mapa.has(clave)) {
            mapa.set(clave, {
                modelo: producto.modelo,
                foto: producto.foto,
                talles: (producto.talles || []).map(t => ({ ...t })),
            });
            orden.push(clave);
            return;
        }

        const existente = mapa.get(clave);

        // Si la primera entrada que apareció no tenía foto pero esta sí, usamos esta.
        if (!existente.foto && producto.foto) {
            existente.foto = producto.foto;
        }

        (producto.talles || []).forEach(t => {
            const yaEstaba = existente.talles.find(x => String(x.talle) === String(t.talle));
            if (yaEstaba) {
                // Mismo talle repetido en los dos lados: se suma el stock.
                yaEstaba.stock = (Number(yaEstaba.stock) || 0) + (Number(t.stock) || 0);
            } else {
                existente.talles.push({ ...t });
            }
        });
    });

    // Ordenamos los talles de cada producto ya fusionado (numérico si se
    // puede, si no alfabético) para que se muestren prolijos de menor a mayor.
    orden.forEach(clave => {
        const producto = mapa.get(clave);
        producto.talles.sort((a, b) => {
            const na = parseInt(a.talle, 10);
            const nb = parseInt(b.talle, 10);
            if (!isNaN(na) && !isNaN(nb)) return na - nb;
            return String(a.talle).localeCompare(String(b.talle));
        });
    });

    return orden.map(clave => mapa.get(clave));
}