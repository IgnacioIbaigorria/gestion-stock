import sqlite3
from datetime import datetime
from signals import signals  # Importa la instancia global

def crear_tablas():
    conn = sqlite3.connect("kiosco.db")
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
            margen_ganancia REAL
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
    
    #Tabla de deudas cliente
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deudas (
            id INTEGER PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            venta_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            monto REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (venta_id) REFERENCES ventas(id)
        )
    ''')

    #Tabla de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            monto REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    conn.commit()
    conn.close()


#Productos
def existe_producto(codigo_barras, nombre):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM productos
        WHERE codigo_barras = ? OR nombre = ?
    ''', (codigo_barras, nombre))
    existe = cursor.fetchone()[0] > 0
    conn.close()
    return existe

def fetch_productos():
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nombre FROM productos')
        nombres_productos = [row[0] for row in cursor.fetchall()]
        return nombres_productos
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def agregar_producto(codigo_barras, nombre, costo, venta, margen, cantidad, venta_por_peso):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (codigo_barras, nombre, venta_por_peso, cantidad, costo, venta, margen))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def actualizar_producto(codigo_barras, nombre, costo, venta, margen, cantidad, venta_por_peso):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE productos SET nombre=?, venta_por_peso=?, disponible=?, precio_costo=?, precio_venta=?, margen_ganancia=?
        WHERE codigo_barras=? or nombre=?
    ''', (nombre, venta_por_peso, cantidad, costo, venta, margen, codigo_barras, nombre))
    conn.commit()
    rows_updated = cursor.rowcount
    conn.close()
    return rows_updated > 0

def eliminar_producto(codigo_o_nombre):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE codigo_barras=? or nombre=?", (codigo_o_nombre, codigo_o_nombre,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

def buscar_producto(term):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    term = f"%{term}%"
    cursor.execute('''
        SELECT codigo_barras, nombre, ROUND(disponible,3), venta_por_peso, precio_costo, precio_venta, margen_ganancia 
        FROM productos 
        WHERE nombre LIKE ? OR codigo_barras LIKE ?
    ''', (term, term))
    productos = cursor.fetchall()
    conn.close()
    return productos


#Ventas

def buscar_coincidencias_producto(termino):
    conn = sqlite3.connect("kiosco.db")
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
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo_barras, nombre, precio_costo, precio_venta, margen_ganancia, venta_por_peso, disponible
        FROM productos 
        WHERE codigo_barras = ? OR nombre = ?
    ''', (codigo_o_nombre, codigo_o_nombre))
    producto = cursor.fetchone()
    conn.close()
    return producto

def obtener_producto_por_id(producto_id):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo_barras, nombre, precio_costo, precio_venta, margen_ganancia, venta_por_peso, disponible
        FROM productos 
        WHERE id = ?
    ''', (producto_id,))
    producto = cursor.fetchone()
    conn.close()
    return producto


def registrar_venta(lista_productos, total, metodo_pago, cliente_id=None):
    conn = sqlite3.connect("kiosco.db")
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Insertar la venta en la tabla ventas
        cursor.execute('''
            INSERT INTO ventas (fecha, monto_total, metodo_pago) VALUES (?, ?, ?)
        ''', (fecha_actual, total, metodo_pago))
        venta_id = cursor.lastrowid

        # Insertar productos en detalle_ventas y actualizar stock
        for producto in lista_productos:
            producto_id, cantidad, precio = producto
            cursor.execute('SELECT disponible FROM productos WHERE id = ?', (producto_id,))
            stock_disponible = cursor.fetchone()

            if stock_disponible is None or stock_disponible[0] < cantidad:
                raise Exception(f"Stock insuficiente para el producto con ID {producto_id}")

            cursor.execute('''
                INSERT INTO detalle_ventas (venta_id, producto_id, cantidad) VALUES (?, ?, ?)
            ''', (venta_id, producto_id, cantidad))
            cursor.execute('''
                UPDATE productos SET disponible = ROUND(disponible - ?, 3) WHERE id = ?
            ''', (cantidad, producto_id))

        if metodo_pago == "A Crédito" and cliente_id is not None:
            cursor.execute(
                "INSERT INTO deudas (cliente_id, venta_id, fecha, monto) VALUES (?, ?, datetime('now'), ?)",
                (cliente_id, venta_id, total)
            )

        
        conn.commit()
        signals.venta_realizada.emit()  # Emite la señal después de registrar la venta
        return True, venta_id
    except Exception as e:
        print("Error al registrar venta:", e)
        conn.rollback()
        return False, None
    finally:
        conn.close()
        

#Caja

def obtener_detalle_ventas(venta_id):
    conn = sqlite3.connect("kiosco.db")
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
    conn = sqlite3.connect("kiosco.db")
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
    conn = sqlite3.connect("kiosco.db")
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
    conn = sqlite3.connect("kiosco.db")
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

#Clientes

def agregar_cliente_a_db(nombre):
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clientes (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al agregar cliente: {e}")
        return False

def obtener_clientes():
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM clientes")
        clientes = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]
        conn.close()
        return clientes
    except Exception as e:
        print(f"Error al obtener clientes: {e}")
        return []

def obtener_deudas_cliente(cliente_id):
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, monto FROM deudas WHERE cliente_id = ?", (cliente_id,))
        deudas = [{"fecha": row[0], "monto": row[1]} for row in cursor.fetchall()]
        conn.close()
        return deudas
    except Exception as e:
        print(f"Error al obtener deudas: {e}")
        return []

def obtener_pagos_cliente(cliente_id):
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, monto FROM pagos WHERE cliente_id = ?", (cliente_id,))
        pagos = [{"fecha": row[0], "monto": row[1]} for row in cursor.fetchall()]
        conn.close()
        return pagos
    except Exception as e:
        print(f"Error al obtener pagos: {e}")
        return []

def obtener_detalle_ventas_deudas(cliente_id):
    """Obtiene las deudas de un cliente con el detalle completo de las ventas."""
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()

        # Consultar las deudas junto con los detalles de las ventas
        cursor.execute("""
            SELECT d.fecha, d.monto, v.id AS venta_id
            FROM deudas d
            JOIN ventas v ON d.venta_id = v.id
            WHERE d.cliente_id = ?
        """, (cliente_id,))
        deudas = cursor.fetchall()

        # Para cada deuda, obtener el detalle completo de la venta
        resultados = []
        for deuda in deudas:
            fecha, monto, venta_id = deuda
            cursor.execute("""
                SELECT p.nombre, dv.cantidad, p.precio_venta
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                WHERE dv.venta_id = ?
            """, (venta_id,))
            detalle = [{"nombre": row[0], "cantidad": row[1], "precio_unitario": row[2]} for row in cursor.fetchall()]
            resultados.append({"fecha": fecha, "monto": monto, "detalle": detalle})

        conn.close()
        return resultados
    except Exception as e:
        print(f"Error al obtener detalles de ventas: {e}")
        return []

def registrar_pago_cliente(cliente_id, monto):
    try:
        conn = sqlite3.connect("kiosco.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pagos (cliente_id, fecha, monto) VALUES (?, datetime('now'), ?)",
            (cliente_id, monto)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al registrar pago: {e}")
        return False
