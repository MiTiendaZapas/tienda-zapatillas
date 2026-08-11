import os

ARCHIVO_STOCK = "stock_proveedor.txt"
CARPETA_FOTOS = "Fotos"
ARCHIVO_JS = "catalogo.js"

def limpiar_nombre_archivo(nombre):
    if not nombre:
        return ""
    nombre_limpio = nombre.replace("/", " ").replace("\\", " ").replace("\u00a0", " ")
    return " ".join(nombre_limpio.split())

def main():
    if not os.path.exists(ARCHIVO_STOCK):
        print(f"❌ No encontré {ARCHIVO_STOCK}.")
        return

    with open(ARCHIVO_STOCK, "r", encoding="utf-8") as f:
        lineas = f.read().strip().split('\n')

    productos = []
    extensiones = ['.jpg', '.jpeg', '.png', '.webp']

    for i in range(0, len(lineas), 3):
        if i + 1 < len(lineas):
            modelo_original = lineas[i].strip()
            talles_crudos = lineas[i+1].strip()
            
            if not modelo_original or not talles_crudos:
                continue

            # Extraer talles reales
            talles_lista = []
            partes = talles_crudos.split(',')
            for p in partes:
                p = p.strip()
                if 'al' in p:
                    extremos = p.split('al')
                    try:
                        inicio = int(extremos[0].strip())
                        fin = int(extremos[1].strip())
                        talles_lista.extend(list(range(inicio, fin + 1)))
                    except:
                        pass
                else:
                    try:
                        talles_lista.append(int(p))
                    except:
                        pass

            # Buscar foto
            nombre_archivo = limpiar_nombre_archivo(modelo_original)
            ruta_foto_final = ""
            for ext in extensiones:
                ruta_prueba = os.path.join(CARPETA_FOTOS, f"{nombre_archivo}{ext}")
                if os.path.exists(ruta_prueba):
                    ruta_foto_final = f"Fotos/{nombre_archivo}{ext}"
                    break

            if ruta_foto_final:
                productos.append({
                    "modelo": modelo_original,
                    "talles": talles_lista,
                    "foto": ruta_foto_final
                })

    # Escribir el catálogo sin precios
    with open(ARCHIVO_JS, "w", encoding="utf-8") as f:
        f.write("const stock_actualizado = [\n")
        for p in productos:
            f.write(f"  {{ modelo: '{p['modelo']}', talles: {p['talles']}, foto: '{p['foto']}' }},\n")
        f.write("];\n")

    print(f"✅ Catálogo web generado con {len(productos)} productos.")

if __name__ == "__main__":
    main()