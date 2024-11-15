import sqlite3
from datetime import datetime

def crear_tablas():
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()

    # Tabla Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            codigo_barras TEXT UNIQUE,
            nombre TEXT,
            venta_por_peso INTEGER, -- 0 = por unidad, 1 = por peso
            disponible REAL,        -- Admite enteros o reales según el tipo de venta
            precio_costo REAL,
            precio_venta REAL,
            margen_ganancia REAL,
            familia TEXT
        )
    ''')

    # Tabla Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY,
            fecha TEXT,
            monto_total REAL,
            metodo_pago TEXT
        )
    ''')

    # Tabla Detalle de Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY,
            venta_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            FOREIGN KEY(venta_id) REFERENCES ventas(id),
            FOREIGN KEY(producto_id) REFERENCES productos(id)
        )
    ''')

    conn.commit()
    conn.close()

#Productos
def existe_producto(codigo_barras, nombre):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM productos
        WHERE codigo_barras = ? OR nombre = ?
    ''', (codigo_barras, nombre))
    existe = cursor.fetchone()[0] > 0
    conn.close()
    return existe

def agregar_producto(codigo_barras, nombre, costo, venta, margen, familia, cantidad, venta_por_peso):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia, familia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (codigo_barras, nombre, venta_por_peso, cantidad, costo, venta, margen, familia))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def actualizar_producto(codigo_barras, nombre, costo, venta, margen, familia, cantidad, venta_por_peso):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE productos SET nombre=?, venta_por_peso=?, disponible=?, precio_costo=?, precio_venta=?, margen_ganancia=?, familia=?
        WHERE codigo_barras=?
    ''', (nombre, venta_por_peso, cantidad, costo, venta, margen, familia, codigo_barras))
    conn.commit()
    rows_updated = cursor.rowcount
    conn.close()
    return rows_updated > 0

def eliminar_producto(codigo_barras):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE codigo_barras=?", (codigo_barras,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

def buscar_producto(term):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    term = f"%{term}%"
    cursor.execute('''
        SELECT codigo_barras, nombre, ROUND(disponible,3), venta_por_peso, precio_costo, precio_venta, margen_ganancia, familia 
        FROM productos 
        WHERE nombre LIKE ? OR codigo_barras LIKE ?
    ''', (term, term))
    productos = cursor.fetchall()
    conn.close()
    return productos

def buscar_producto_por_familia(term, familia):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    
    # Si la familia es "Todas", buscar sin filtrar por familia
    term = f"%{term}%"
    if familia == "Todas":
        cursor.execute('''
            SELECT codigo_barras, nombre, ROUND(disponible,3), venta_por_peso, precio_costo, precio_venta, margen_ganancia, familia
            FROM productos 
            WHERE nombre LIKE ? OR codigo_barras LIKE ?
        ''', (term, term))
    else:
        cursor.execute('''
            SELECT codigo_barras, nombre, disponible, venta_por_peso, precio_costo, precio_venta, margen_ganancia, familia 
            FROM productos 
            WHERE (nombre LIKE ? OR codigo_barras LIKE ?) AND familia = ?
        ''', (term, term, familia))
    
    productos = cursor.fetchall()
    conn.close()
    return productos


#Ventas

def buscar_coincidencias_producto(termino):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    termino = f"%{termino}%"
    cursor.execute('''
        SELECT nombre FROM productos
        WHERE nombre LIKE ? OR codigo_barras LIKE ?
        LIMIT 10
    ''', (termino, termino))
    resultados = [fila[0] for fila in cursor.fetchall()]
    conn.close()
    return resultados

def obtener_producto_por_codigo(codigo_o_nombre):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo_barras, nombre, precio_costo, precio_venta, margen_ganancia, familia, venta_por_peso, disponible
        FROM productos 
        WHERE codigo_barras = ? OR nombre = ?
    ''', (codigo_o_nombre, codigo_o_nombre))
    producto = cursor.fetchone()
    conn.close()
    return producto

def obtener_producto_por_id(producto_id):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo_barras, nombre, precio_costo, precio_venta, margen_ganancia, familia, venta_por_peso
        FROM productos 
        WHERE id = ?
    ''', (producto_id,))
    producto = cursor.fetchone()
    conn.close()
    return producto


def registrar_venta(lista_productos, total, metodo_pago):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Insertar la venta en la tabla ventas
        cursor.execute('''
            INSERT INTO ventas (fecha, monto_total, metodo_pago) VALUES (?, ?, ?)
        ''', (fecha_actual, total, metodo_pago))
        venta_id = cursor.lastrowid  # Obtener el ID de la venta recién insertada

        # Insertar cada producto en la tabla detalle_ventas y actualizar el stock
        for producto in lista_productos:
            producto_id, cantidad, precio = producto
            
            # Comprobación de stock antes de insertar en detalle_ventas
            cursor.execute('''
                SELECT disponible FROM productos WHERE id = ?
            ''', (producto_id,))
            stock_disponible = cursor.fetchone()

            if stock_disponible is None:
                raise Exception(f"El producto con ID {producto_id} no existe.")
            elif stock_disponible[0] < cantidad:
                raise Exception(f"Stock insuficiente para el producto con ID {producto_id}")

            # Insertar el producto en el detalle de la venta
            cursor.execute('''
                INSERT INTO detalle_ventas (venta_id, producto_id, cantidad) 
                VALUES (?, ?, ?)
            ''', (venta_id, producto_id, cantidad))

            # Actualizar el stock en la tabla de productos
            cursor.execute('''
                UPDATE productos
                SET disponible = ROUND(disponible - ?, 3)
                WHERE id = ?
            ''', (cantidad, producto_id))

        conn.commit()
        return True, venta_id
    except Exception as e:
        print("Error al registrar venta:", e)
        conn.rollback()
        return False, None
    finally:
        conn.close()

#Caja

def obtener_detalle_ventas(venta_id):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.nombre, dv.cantidad 
        FROM detalle_ventas dv
        JOIN productos p ON dv.producto_id = p.id
        WHERE dv.venta_id = ?
    ''', (venta_id,))
    detalles = cursor.fetchall()
    conn.close()
    
    # Formatear los detalles en una cadena para mostrar en la tabla de caja
    detalles_texto = "; ".join(
        f"{nombre} (x{cantidad:.2f} kg)" if isinstance(cantidad, float) and not cantidad.is_integer() else f"{nombre} (x{int(cantidad)})"
        for nombre, cantidad in detalles
    )
    return detalles_texto

def obtener_detalle_ventas(venta_id):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.nombre, dv.cantidad, p.precio_costo, p.precio_venta 
        FROM detalle_ventas dv
        JOIN productos p ON dv.producto_id = p.id
        WHERE dv.venta_id = ?
    ''', (venta_id,))
    detalle = cursor.fetchall()
    conn.close()
    return detalle

def obtener_ventas_por_dia(fecha):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
        FROM ventas v
        WHERE date(v.fecha) = ?
    ''', (fecha,))
    ventas = cursor.fetchall()
    conn.close()

    # Añadir el detalle de productos y calcular la ganancia por venta
    ventas_con_detalle = []
    for venta in ventas:
        fecha, monto_total, metodo_pago, venta_id = venta
        detalle = obtener_detalle_ventas(venta_id)
        
        # Calcular ganancia de la venta
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)  # (precio_venta - precio_costo) * cantidad
        ventas_con_detalle.append((fecha, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle

def obtener_ventas_por_periodo(fecha_inicio, fecha_fin):
    conn = sqlite3.connect("carniceria.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
        FROM ventas v
        WHERE date(v.fecha) BETWEEN ? AND ?
    ''', (fecha_inicio, fecha_fin))
    ventas = cursor.fetchall()
    conn.close()

    # Añadir el detalle de productos y calcular la ganancia por venta
    ventas_con_detalle = []
    for venta in ventas:
        fecha, monto_total, metodo_pago, venta_id = venta
        detalle = obtener_detalle_ventas(venta_id)
        
        # Calcular ganancia de la venta
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)  # (precio_venta - precio_costo) * cantidad
        ventas_con_detalle.append((fecha, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle
