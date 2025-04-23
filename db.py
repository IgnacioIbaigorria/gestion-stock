import sqlite3
from datetime import datetime
from signals import signals  # Importa la instancia global
from config import get_db_path
import hashlib
import pytz

def crear_tablas():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('administrador', 'empleado')),
            ultima_conexion DATETIME,
            ultima_desconexion DATETIME
        )
    ''')
    
    # Tabla Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY,
            codigo_barras TEXT,
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

    # Crear tabla de modificaciones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS modificaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tipo_modificacion TEXT NOT NULL,  -- 'ALTA', 'BAJA', 'MODIFICACION'
        producto_id INTEGER,
        campo_modificado TEXT,            -- NULL para ALTA/BAJA
        valor_anterior TEXT,              -- NULL para ALTA
        valor_nuevo TEXT,                 -- NULL para BAJA
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )
    ''')

    conn.commit()
    conn.close()


#Productos
def existe_producto(codigo_barras, nombre):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # Si hay código de barras, verificar ambos
    if codigo_barras:
        cursor.execute('''
            SELECT COUNT(*) FROM productos
            WHERE codigo_barras = ? OR nombre = ?
        ''', (codigo_barras, nombre))
    else:
        # Si no hay código de barras, verificar solo el nombre
        cursor.execute('''
            SELECT COUNT(*) FROM productos
            WHERE nombre = ?
        ''', (nombre,))
    
    existe = cursor.fetchone()[0] > 0
    conn.close()
    return existe

def fetch_productos():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nombre FROM productos')
        nombres_productos = [row[0] for row in cursor.fetchall()]
        return nombres_productos
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def registrar_modificacion(cursor, usuario, tipo_modificacion, producto_id, campo_modificado=None, valor_anterior=None, valor_nuevo=None):
    try:
        print(f"""
        Registrando modificación:
        Usuario: {usuario}
        Tipo: {tipo_modificacion}
        Producto ID: {producto_id}
        Campo: {campo_modificado}
        Valor anterior: {valor_anterior}
        Valor nuevo: {valor_nuevo}
        """)
        
        # Obtener la hora actual en el huso horario de Argentina
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_hora_argentina = datetime.now(argentina_tz)  # Hora en Argentina
        
        # Convertir a UTC
        fecha_hora_utc = fecha_hora_argentina.astimezone(pytz.utc)  # Convertir a UTC
        
        cursor.execute('''
            INSERT INTO modificaciones (usuario, fecha_hora, tipo_modificacion, producto_id, campo_modificado, valor_anterior, valor_nuevo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (usuario, fecha_hora_utc, tipo_modificacion, producto_id, campo_modificado, valor_anterior, valor_nuevo))
        
        return True
    except sqlite3.Error as e:
        print(f"Error al registrar modificación: {e}")
        return False
    
def agregar_producto(codigo_barras, nombre, costo, venta, margen, cantidad, venta_por_peso, usuario):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (codigo_barras, nombre, venta_por_peso, cantidad, costo, venta, margen))
        
        producto_id = cursor.lastrowid
        
        # Usar el mismo cursor para registrar la modificación
        registrar_modificacion(cursor, usuario, 'ALTA', producto_id)
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error al agregar producto: {e}")
        return False
    finally:
        conn.close()

def actualizar_producto(codigo_barras=None, nombre=None, costo=None, venta=None, margen=None, cantidad=None, venta_por_peso=None, usuario=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        # Obtener el producto actual
        if nombre is not None:
            cursor.execute("SELECT * FROM productos WHERE nombre=?", (nombre,))
        elif codigo_barras is not None:
            cursor.execute("SELECT * FROM productos WHERE codigo_barras=?", (codigo_barras,))
        else:
            return False

        producto_actual = cursor.fetchone()
        if not producto_actual:
            return False

        # Mapear los índices de las columnas para mayor claridad
        ID, COD_BARRAS, NOMBRE, VENTA_PESO, DISPONIBLE, COSTO, VENTA, MARGEN = range(8)

        # Registrar modificaciones de cada campo
        campos_modificados = []
        
        # Verificar cambios en código de barras
        if codigo_barras != producto_actual[COD_BARRAS]:
            campos_modificados.append(('codigo_barras', 
                                    str(producto_actual[COD_BARRAS]), 
                                    str(codigo_barras)))
        
        # Verificar cambios en nombre
        if nombre != producto_actual[NOMBRE]:
            campos_modificados.append(('nombre', 
                                    str(producto_actual[NOMBRE]), 
                                    str(nombre)))
        
        # Verificar cambio en tipo de venta
        if venta_por_peso != producto_actual[VENTA_PESO]:
            campos_modificados.append(('venta_por_peso', 
                                    str(producto_actual[VENTA_PESO]), 
                                    str(venta_por_peso)))
        
        # Verificar cambio en cantidad
        try:
            if float(cantidad) != float(producto_actual[DISPONIBLE]):
                campos_modificados.append(('disponible', 
                                        str(producto_actual[DISPONIBLE]), 
                                        str(cantidad)))
        except (ValueError, TypeError):
            pass

        # Verificar cambio en costo
        try:
            if float(costo) != float(producto_actual[COSTO]):
                campos_modificados.append(('precio_costo', 
                                        str(producto_actual[COSTO]), 
                                        str(costo)))
        except (ValueError, TypeError):
            pass

        # Verificar cambio en precio de venta
        try:
            if float(venta) != float(producto_actual[VENTA]):
                campos_modificados.append(('precio_venta', 
                                        str(producto_actual[VENTA]), 
                                        str(venta)))
        except (ValueError, TypeError):
            pass

        # Verificar cambio en margen
        try:
            if float(margen) != float(producto_actual[MARGEN]):
                campos_modificados.append(('margen_ganancia', 
                                        str(producto_actual[MARGEN]), 
                                        str(margen)))
        except (ValueError, TypeError):
            pass

        # Si hay cambios, actualizar el producto
        if campos_modificados:
            # Actualizar producto
            cursor.execute('''
                UPDATE productos 
                SET codigo_barras=?, nombre=?, venta_por_peso=?, disponible=?, 
                    precio_costo=?, precio_venta=?, margen_ganancia=?
                WHERE id=?
            ''', (codigo_barras, nombre, venta_por_peso, cantidad, 
                  costo, venta, margen, producto_actual[ID]))

            # Registrar todas las modificaciones
            print(f"Campos modificados para producto {producto_actual[ID]}:")
            for campo, valor_anterior, valor_nuevo in campos_modificados:
                print(f"Campo: {campo}, Anterior: {valor_anterior}, Nuevo: {valor_nuevo}")
                registrar_modificacion(cursor, usuario, 'MODIFICACION', 
                                    producto_actual[ID], campo, 
                                    valor_anterior, valor_nuevo)

            conn.commit()
            return True
        else:
            print("No se detectaron cambios en el producto")
            return True

    except sqlite3.Error as e:
        print(f"Error en actualizar_producto: {e}")
        return False
    finally:
        conn.close()

def eliminar_producto(codigo_o_nombre):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE codigo_barras=? or nombre=?", (codigo_o_nombre, codigo_o_nombre,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

def buscar_producto(term):
    conn = sqlite3.connect(get_db_path())
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
    conn = sqlite3.connect(get_db_path())
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
    conn = sqlite3.connect(get_db_path())
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
    conn = sqlite3.connect(get_db_path())
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
    conn = sqlite3.connect(get_db_path())
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
                "INSERT INTO deudas (cliente_id, venta_id, fecha, monto_total, monto) VALUES (?, ?, datetime('now'), ?, ?)",
                (cliente_id, venta_id, total, total)
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
    conn = sqlite3.connect(get_db_path())
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

def obtener_detalle_ventas1(venta_id):
    conn = sqlite3.connect(get_db_path())
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
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
        FROM ventas v
        WHERE date(v.fecha) = ? AND v.metodo_pago != 'Pago de deuda'
    ''', (fecha,))
    ventas = cursor.fetchall()
    conn.close()

    # Añadir el detalle de productos y calcular la ganancia por venta
    ventas_con_detalle = []
    for venta in ventas:
        fecha_str, monto_total, metodo_pago, venta_id = venta
        # Verificar si la fecha tiene hora
        if " " in fecha_str:
            # Convertir la fecha y hora al formato deseado
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
        else:
            # Solo convertir la fecha
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        
        detalle = obtener_detalle_ventas1(venta_id)
        print("Detalle:", detalle)
        
        # Calcular la ganancia
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)  # Asegúrate de que los índices sean correctos
        
        # Imprimir detalles de la venta
        print("Venta:", venta_id)
        for item in detalle:
            print("precio de venta:", item[3])
            print("costo:", item[2])
            print("cantidad:", item[1])
        
        # Imprimir la ganancia calculada
        print("ganancia:", ganancia)  # Asegúrate de que esto imprima el valor correcto
        
        # Agregar a la lista de ventas con detalle
        ventas_con_detalle.append((fecha_formateada, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle

def obtener_ventas_por_periodo(fecha_inicio, fecha_fin):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
        FROM ventas v
        WHERE date(v.fecha) BETWEEN ? AND ? AND v.metodo_pago != 'Pago de deuda'
    ''', (fecha_inicio, fecha_fin))
    ventas = cursor.fetchall()
    conn.close()

    ventas_con_detalle = []
    for venta in ventas:
        fecha_str, monto_total, metodo_pago, venta_id = venta
        # Verificar si la fecha tiene hora
        if " " in fecha_str:
            # Convertir la fecha y hora al formato deseado
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
        else:
            # Solo convertir la fecha
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        
        detalle = obtener_detalle_ventas1(venta_id)
        print("Detalle:", detalle)
        
        # Calcular la ganancia
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)  # Asegúrate de que los índices sean correctos
        
        # Imprimir detalles de la venta
        print("Venta:", venta_id)
        for item in detalle:
            print("precio de venta:", item[3])
            print("costo:", item[2])
            print("cantidad:", item[1])
        
        # Imprimir la ganancia calculada
        print("ganancia:", ganancia)  # Asegúrate de que esto imprima el valor correcto
        
        # Agregar a la lista de ventas con detalle
        ventas_con_detalle.append((fecha_formateada, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle

def obtener_total_ventas_efectivo(fecha):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(monto_total) FROM ventas WHERE fecha = ? AND metodo_pago = 'Efectivo'
    ''', (fecha,))
    total_efectivo = cursor.fetchone()[0] or 0  # Si no hay ventas, devuelve 0
    conn.close()
    return total_efectivo

def registrar_retiro_efectivo(monto):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO retiros_efectivo (monto, fecha) VALUES (?, datetime('now'))
        ''', (monto,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar retiro: {e}")
        return False
    finally:
        conn.close()
        
def obtener_retiros_por_dia(fecha):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(monto) FROM retiros_efectivo WHERE DATE(fecha) = ?
    ''', (fecha,))
    total_retiros = cursor.fetchone()[0] or 0  # Si no hay retiros, devuelve 0
    conn.close()
    return total_retiros

def obtener_todos_los_retiros():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT monto, fecha FROM retiros_efectivo
    ''')
    retiros = cursor.fetchall()  # Obtiene todos los retiros
    conn.close()

    # Formatear las fechas
    retiros_formateados = []
    for monto, fecha in retiros:
        # Verificar si la fecha contiene hora
        if " " in fecha:
            # Formato con hora
            fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        else:
            # Formato solo con fecha
            fecha_formateada = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        
        retiros_formateados.append((monto, fecha_formateada))

    return retiros_formateados

#Clientes

def agregar_cliente_a_db(nombre):
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clientes (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()
        signals.cliente_agregado.emit()
        return True
    except Exception as e:
        print(f"Error al agregar cliente: {e}")
        return False

def obtener_clientes():
    try:
        conn = sqlite3.connect(get_db_path())
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
        conn = sqlite3.connect(get_db_path())
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
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT fecha, monto , venta_id FROM pagos WHERE cliente_id = ?", (cliente_id,))
        pagos = [{"fecha": row[0], "monto": row[1] , "venta_id": row[2]} for row in cursor.fetchall()]
        conn.close()
        return pagos
    except Exception as e:
        print(f"Error al obtener pagos: {e}")
        return []

def obtener_detalle_ventas_deudas(cliente_id):
    """Obtiene las deudas de un cliente con el detalle completo de las ventas."""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Consultar las deudas de ventas regulares
        cursor.execute("""
            SELECT d.fecha, d.monto, v.id AS venta_id, v.monto_total
            FROM deudas d
            JOIN ventas v ON d.venta_id = v.id
            WHERE d.cliente_id = ?
        """, (cliente_id,))
        deudas = cursor.fetchall()

        # Para cada deuda, obtener el detalle completo de la venta
        resultados = []
        for deuda in deudas:
            fecha, monto, venta_id, monto_total = deuda
            cursor.execute("""
                SELECT p.nombre, dv.cantidad, p.precio_costo, p.precio_venta
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                WHERE dv.venta_id = ?
            """, (venta_id,))
            
            # Procesar el detalle de la venta
            detalle = []
            for row in cursor.fetchall():
                nombre = row[0] if row[0] else "Producto Desconocido"
                cantidad = row[1]
                precio_venta = row[3] if len(row) > 3 else 0
                detalle.append({
                    "nombre": nombre,
                    "cantidad": cantidad,
                    "precio_unitario": precio_venta
                })

            # Obtener el monto pagado para esta venta
            cursor.execute("""
                SELECT SUM(p.monto) 
                FROM pagos p 
                WHERE p.venta_id = ?
            """, (venta_id,))
            monto_pagado = cursor.fetchone()[0] or 0

            resultados.append({
                "fecha": fecha,
                "monto": monto,
                "monto_total": monto_total,
                "monto_pagado": monto_pagado,
                "venta_id": venta_id,
                "detalle": detalle
            })

        conn.close()
        return resultados
    except Exception as e:
        print(f"Error al obtener detalles de ventas: {e}")
        return []

def registrar_pago_cliente(cliente_id, monto):
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()

        # Obtener las deudas pendientes del cliente, ordenadas por fecha (primero las más antiguas)
        cursor.execute("""
            SELECT id, venta_id, monto 
            FROM deudas 
            WHERE cliente_id = ? 
            ORDER BY fecha
        """, (cliente_id,))
        deudas = cursor.fetchall()

        if not deudas:
            raise Exception("El cliente no tiene deudas pendientes.")

        # Procesar el pago contra las deudas
        monto_restante = monto
        index = 0  # Índice para iterar sobre las deudas

        while monto_restante > 0 and index < len(deudas):
            deuda_id, venta_id, monto_deuda = deudas[index]

            if monto_restante >= monto_deuda:
                # Pagar completamente la deuda
                cursor.execute("DELETE FROM deudas WHERE id = ?", (deuda_id,))
                monto_restante -= monto_deuda
                # Registrar el pago asociado a esta venta
                cursor.execute("""
                    INSERT INTO pagos (cliente_id, fecha, monto, venta_id)
                    VALUES (?, datetime('now'), ?, ?)
                """, (cliente_id, monto_deuda, venta_id))  # Asocia el pago a la venta_id
            else:
                # Pagar parcialmente la deuda
                nuevo_monto = monto_deuda - monto_restante
                cursor.execute("UPDATE deudas SET monto = ? WHERE id = ?", (nuevo_monto, deuda_id))
                # Registrar el pago asociado a esta venta
                cursor.execute("""
                    INSERT INTO pagos (cliente_id, fecha, monto, venta_id)
                    VALUES (?, datetime('now'), ?, ?)
                """, (cliente_id, monto_restante, venta_id))  # Asocia el pago a la venta_id
                monto_restante = 0  # Ya no queda monto restante

            index += 1  # Avanzar al siguiente índice de deuda

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al registrar pago: {e}")
        return False

# Usuarios

def hash_password(password):
    """Convierte la contraseña en un hash seguro."""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_credenciales(nombre_usuario, password):
    """Verifica las credenciales del usuario y actualiza última conexión."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        # Obtener el usuario y su rol
        cursor.execute('''
            SELECT id, rol, contrasena 
            FROM usuarios 
            WHERE nombre = ?
        ''', (nombre_usuario,))
        
        resultado = cursor.fetchone()
        
        if resultado and resultado[2] == hash_password(password):
            # Actualizar última conexión
            cursor.execute('''
                UPDATE usuarios 
                SET ultima_conexion = ? 
                WHERE id = ?
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), resultado[0]))
            
            conn.commit()
            return True, resultado[1]  # Retorna (éxito, rol)
        return False, None
    
    except Exception as e:
        print(f"Error en verificación de credenciales: {e}")
        return False, None
    finally:
        conn.close()

def crear_usuario_admin_default():
    """Crea un usuario administrador por defecto si no existe ningún usuario."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        # Verificar si hay usuarios en la tabla
        cursor.execute('SELECT COUNT(*) FROM usuarios')
        if cursor.fetchone()[0] == 0:
            # Crear usuario admin por defecto
            cursor.execute('''
                INSERT INTO usuarios (nombre, contrasena, rol, ultima_conexion)
                VALUES (?, ?, ?, ?)
            ''', ('admin', hash_password('admin123'), 'administrador', 
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            print("Usuario administrador por defecto creado")
    except Exception as e:
        print(f"Error al crear usuario admin por defecto: {e}")
    finally:
        conn.close()

def obtener_usuarios():
    """Obtiene la lista de usuarios con sus IDs."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, nombre, rol, ultima_conexion, ultima_desconexion 
            FROM usuarios
        ''')
        usuarios = cursor.fetchall()
        return [
            {
                'id': usuario[0],
                'nombre': usuario[1],
                'rol': usuario[2],
                'ultima_conexion': usuario[3],
                'ultima_desconexion': usuario[4]
            }
            for usuario in usuarios
        ]
    finally:
        conn.close()

def crear_usuario(nombre, password, rol):
    """Crea un nuevo usuario."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO usuarios (nombre, contrasena, rol)
            VALUES (?, ?, ?)
        ''', (nombre, hash_password(password), rol))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        return False
    finally:
        conn.close()

def modificar_usuario(id_usuario, nuevo_nombre, password, rol):
    """Modifica un usuario existente usando su ID."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        if password:  # Si se proporciona una nueva contraseña
            cursor.execute('''
                UPDATE usuarios
                SET nombre = ?, contrasena = ?, rol = ?
                WHERE id = ?
            ''', (nuevo_nombre, hash_password(password), rol, id_usuario))
        else:  # Si no se cambia la contraseña
            cursor.execute('''
                UPDATE usuarios
                SET nombre = ?, rol = ?
                WHERE id = ?
            ''', (nuevo_nombre, rol, id_usuario))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al modificar usuario: {e}")
        return False
    finally:
        conn.close()

def registrar_desconexion(nombre_usuario):
    """Registra la hora de desconexión del usuario."""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE usuarios
            SET ultima_desconexion = ?
            WHERE nombre = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nombre_usuario))
        conn.commit()
    except Exception as e:
        print(f"Error al registrar desconexión: {e}")
    finally:
        conn.close()

def obtener_modificaciones():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT m.id, m.usuario, m.fecha_hora, m.tipo_modificacion, 
                   p.nombre as producto_nombre, m.campo_modificado, 
                   m.valor_anterior, m.valor_nuevo
            FROM modificaciones m
            LEFT JOIN productos p ON m.producto_id = p.id
            ORDER BY m.fecha_hora DESC
        ''')
        
        modificaciones = cursor.fetchall()
        return modificaciones
    
    except sqlite3.Error as e:
        print(f"Error al obtener modificaciones: {e}")
        return []
    
    finally:
        conn.close()

