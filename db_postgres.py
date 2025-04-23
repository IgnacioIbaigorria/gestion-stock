import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2 import pool
from config_postgres import get_db_config
from datetime import datetime
from signals import signals
import hashlib
import pytz
from functools import lru_cache
import time
from cachetools import TTLCache
from contextlib import contextmanager
import logging
import threading


logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_postgres')

config = get_db_config()
DB_CONFIG = config

connection_pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host=DB_CONFIG['host'],
    database=DB_CONFIG['database'],
    user=DB_CONFIG['user'],
    password=DB_CONFIG['password'],
    port=DB_CONFIG['port']
)

@contextmanager
def get_db_connection(expected_slow=False):
    conn = get_connection()
    start_time = time.time()
    try:
        # Set a longer statement timeout (10 minutes)
        cursor = conn.cursor()
        if expected_slow:
            cursor.execute("SET statement_timeout = '600000'")  # 10 minutes in milliseconds
        else:
            cursor.execute("SET statement_timeout = '30000'")   # 30 seconds in milliseconds
        
        yield conn
        
        # Commit the transaction
        conn.commit()
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        # Return the connection to the pool
        elapsed = time.time() - start_time
        if elapsed > 0.5:  # Log if operation took more than 500ms
            logger.info(f"Operación larga esperada ({elapsed:.2f}s) en __enter__")
        connection_pool.putconn(conn)

def return_connection(conn):
    connection_pool.putconn(conn)
                    
def get_connection():
    return connection_pool.getconn()

def check_connection_health():
    """Periodically check and refresh database connections to prevent timeouts"""
    while True:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Simple query to keep the connection alive
                cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.debug("Connection health check successful")
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            # Try to recreate the connection pool if needed
            try:
                global connection_pool
                if connection_pool is None or connection_pool.closed:
                    logger.info("Recreating connection pool")
                    connection_pool = ThreadedConnectionPool(
                        minconn=5,
                        maxconn=20,
                        host=DB_CONFIG['host'],
                        database=DB_CONFIG['database'],
                        user=DB_CONFIG['user'],
                        password=DB_CONFIG['password'],
                        port=DB_CONFIG['port']
                    )
            except Exception as pool_error:
                logger.error(f"Failed to recreate connection pool: {pool_error}")
        
        # Sleep for 5 minutes before next check
        time.sleep(300)  # 5 minutes in seconds

connection_health_thread = threading.Thread(
    target=check_connection_health, 
    daemon=True,  # This ensures the thread will exit when the main program exits
    name="DB-HealthCheck"
)
connection_health_thread.start()



def cleanup_stale_connections():
    """Cleanup stale connections in the pool"""
    try:
        for conn in connection_pool._used.copy():
            if conn.closed:
                connection_pool._used.remove(conn)
                connection_pool._pool.append(conn)
    except Exception as e:
        print(f"Error cleaning up stale connections: {e}")
        
def get_pool_status():
    """Monitor connection pool status"""
    return {
        'min_connections': connection_pool.minconn,
        'max_connections': connection_pool.maxconn,
        'used_connections': len(connection_pool._used),
        'free_connections': len(connection_pool._pool),
    }
    
def cleanup_connections():
    """Emergency cleanup of connections"""
    for conn in connection_pool._used:
        try:
            return_connection(conn)
        except Exception as e:
            print(f"Error cleaning up connection: {e}")

def crear_tablas():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('administrador', 'empleado')),
            ultima_conexion TIMESTAMP,
            ultima_desconexion TIMESTAMP
        )
    ''')
    
    # Tabla Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            monto_total REAL,
            metodo_pago TEXT
        )
    ''')

    # Tabla Detalle de Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            monto REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # Crear tabla de modificaciones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS modificaciones (
        id SERIAL PRIMARY KEY,
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

def crear_indices():
    with get_db_connection(expected_slow=True) as conn:
        with conn.cursor() as cursor:
            # Índices para productos
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo_barras)')
            
            # Índices para ventas
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ventas_metodo ON ventas(metodo_pago)')
            
            # Índices para modificaciones
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_modificaciones_fecha ON modificaciones(fecha_hora)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_modificaciones_usuario ON modificaciones(usuario)')
            
            conn.commit()

#Productos
def existe_producto(codigo_barras, nombre):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if codigo_barras:
                cursor.execute('''
                    SELECT COUNT(*) FROM productos
                    WHERE codigo_barras = %s OR nombre = %s
                ''', (codigo_barras, nombre))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM productos
                    WHERE nombre = %s
                ''', (nombre,))
            
            return cursor.fetchone()[0] > 0        

# Cache for 5 minutes
productos_cache = {}  # Se borra en 5 minutos
@lru_cache(maxsize=128)
def get_cached_productos():
    if "productos" in productos_cache:
        return productos_cache["productos"]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nombre FROM productos
            WHERE nombre NOT LIKE '[ELIMINADO]%'
        ''')
        productos = [row[0] for row in cursor.fetchall()]
        cursor.close()
    
    productos_cache["productos"] = productos
    return productos

def optimizar_base_datos():
    """Ejecuta VACUUM y ANALYZE para optimizar la base de datos"""
    with get_db_connection(expected_slow=True) as conn:
        # Desactivar autocommit para ejecutar comandos de mantenimiento
        old_isolation = conn.isolation_level
        conn.set_isolation_level(0)  # ISOLATION_LEVEL_AUTOCOMMIT
        
        with conn.cursor() as cursor:
            try:
                # VACUUM reconstruye la base de datos, eliminando espacio no utilizado
                cursor.execute("VACUUM")
                # ANALYZE actualiza las estadísticas usadas por el planificador de consultas
                cursor.execute("ANALYZE")
                logger.info("Base de datos optimizada correctamente")
            except Exception as e:
                logger.error(f"Error al optimizar la base de datos: {e}")
        
        # Restaurar nivel de aislamiento
        conn.set_isolation_level(old_isolation)

# Use this function instead of direct database calls for product lists
def fetch_productos():
    return get_cached_productos()

# Add this to clear cache when products are modified
def clear_productos_cache():
    productos_cache.clear()
    
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (usuario, fecha_hora_utc, tipo_modificacion, producto_id, campo_modificado, valor_anterior, valor_nuevo))
        
        return True
    except psycopg2.Error as e:  
        print(f"Error al registrar modificación: {e}")
        return False
    
def agregar_producto(codigo_barras, nombre, costo, venta, margen, cantidad, venta_por_peso, usuario):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Insert the product and get its ID
        cursor.execute('''
            INSERT INTO productos (codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (codigo_barras, nombre, venta_por_peso, cantidad, costo, venta, margen))
        
        # Get the actual product ID from the RETURNING clause
        producto_id = cursor.fetchone()[0]
        
        # Register the modification with the correct product ID
        registrar_modificacion(cursor, usuario, 'ALTA', producto_id)
        
        conn.commit()
        clear_productos_cache()  # Clear the cache after adding a product
        return True
    except Exception as e:
        print(f"Error al agregar producto: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        return_connection(conn)
        
        
def actualizar_producto(codigo_barras=None, nombre=None, costo=None, venta=None, margen=None, cantidad=None, venta_por_peso=None, usuario=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener el producto actual
        if nombre is not None:
            cursor.execute("SELECT * FROM productos WHERE nombre=%s", (nombre,))
        elif codigo_barras is not None:
            cursor.execute("SELECT * FROM productos WHERE codigo_barras=%s", (codigo_barras,))
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
                SET codigo_barras=%s, nombre=%s, venta_por_peso=%s, disponible=%s, 
                    precio_costo=%s, precio_venta=%s, margen_ganancia=%s
                WHERE id=%s
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

    except psycopg2.Error as e:  
        print(f"Error en actualizar_producto: {e}")
        return False
    finally:
        conn.close()

def eliminar_producto(codigo_o_nombre, usuario, force_delete=False):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # First get the product ID and details before deletion
                cursor.execute("""
                    SELECT id, codigo_barras, nombre 
                    FROM productos 
                    WHERE codigo_barras=%s OR nombre=%s
                """, (codigo_o_nombre, codigo_o_nombre))
                
                producto = cursor.fetchone()
                if not producto:
                    return False, "Producto no encontrado"
                    
                # Check if product is referenced in sales
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM detalle_ventas 
                    WHERE producto_id = %s
                """, (producto[0],))
                
                has_sales = cursor.fetchone()[0] > 0
                
                if has_sales and not force_delete:
                    return False, "No se puede eliminar el producto porque tiene ventas asociadas. Use force_delete para eliminar de todos modos."
                elif has_sales and force_delete:
                    # Instead of deleting, mark as inactive and keep sales history
                    cursor.execute("""
                        UPDATE productos 
                        SET disponible = 0,
                            nombre = %s
                        WHERE id = %s
                    """, (f"[ELIMINADO] {producto[2]}", producto[0]))
                else:
                    # If no sales, perform actual deletion
                    cursor.execute("""
                        DELETE FROM productos 
                        WHERE id = %s
                    """, (producto[0],))
                
                # Register the modification
                registrar_modificacion(
                    cursor, 
                    usuario, 
                    'BAJA', 
                    producto[0],
                    None,
                    f"Producto: {producto[2]} (Código: {producto[1]})",
                    "Eliminación forzada" if (has_sales and force_delete) else None
                )
                
                conn.commit()
                clear_productos_cache()  # Clear the cache after deletion
                return True, "Producto marcado como eliminado" if (has_sales and force_delete) else "Producto eliminado correctamente"
                
            except Exception as e:
                conn.rollback()
                return False, f"Error al eliminar: {str(e)}"
                                    
def buscar_producto(term=''):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if term:
                cursor.execute('''
                    SELECT id, codigo_barras, nombre, venta_por_peso, disponible, 
                           precio_costo, precio_venta, margen_ganancia 
                    FROM productos 
                    WHERE (LOWER(nombre) LIKE LOWER(%s) OR codigo_barras LIKE %s)
                    AND nombre NOT LIKE '[ELIMINADO]%%'
                ''', (f'%{term}%', f'%{term}%'))
            else:
                cursor.execute('''
                    SELECT id, codigo_barras, nombre, venta_por_peso, disponible, 
                           precio_costo, precio_venta, margen_ganancia 
                    FROM productos
                    WHERE nombre NOT LIKE '[ELIMINADO]%%'
                ''')
            return cursor.fetchall()
                       
#Ventas

def buscar_coincidencias_producto(termino):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            termino = f"%{termino}%"
            cursor.execute('''
                SELECT nombre FROM productos
                WHERE (nombre LIKE %s OR codigo_barras LIKE %s)
                AND nombre NOT LIKE '[ELIMINADO]%%'
                LIMIT 10
            ''', (termino, termino))
            resultados = [fila[0] for fila in cursor.fetchall()]
    return resultados


def obtener_producto_por_codigo(codigo_barras):
    """Versión optimizada para obtener un producto por su código de barras."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Para códigos de peso variable (comienzan con 2 y tienen al menos 7 dígitos)
            es_codigo_peso = len(codigo_barras) >= 7 and codigo_barras.startswith('2')
            codigo_base = codigo_barras[2:7] if es_codigo_peso else codigo_barras
            
            cursor.execute('''
                SELECT id, codigo_barras, nombre, precio_costo, precio_venta, 
                       margen_ganancia, venta_por_peso, disponible
                FROM productos
                WHERE codigo_barras = %s
                   OR (codigo_barras = %s AND %s)
                   OR nombre ILIKE %s
                LIMIT 1
            ''', (codigo_barras, codigo_base, es_codigo_peso, f"%{codigo_barras}%"))
            
            return cursor.fetchone()
            

def obtener_producto_por_id(producto_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT id, codigo_barras, nombre, precio_costo, precio_venta, 
                       margen_ganancia, venta_por_peso, disponible
                FROM productos 
                WHERE id = %s
            ''', (producto_id,))
            return cursor.fetchone()


def registrar_venta(lista_productos, total, metodo_pago, cliente_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 1. Insert venta and get ID in one operation
                cursor.execute('''
                    INSERT INTO ventas (fecha, monto_total, metodo_pago) 
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (fecha_actual, total, metodo_pago))
                venta_id = cursor.fetchone()[0]

                # 2. Prepare data for batch operations
                detalles_values = []
                stock_updates = []
                producto_ids = [producto[0] for producto in lista_productos]

                # 3. Get all product stock in one query
                cursor.execute('''
                    SELECT id, disponible 
                    FROM productos 
                    WHERE id = ANY(%s)
                ''', (producto_ids,))
                stock_actual = dict(cursor.fetchall())

                # 4. Validate stock and prepare batch updates
                for producto_id, cantidad, precio in lista_productos:
                    stock_disponible = stock_actual.get(producto_id)
                    
                    if stock_disponible is None or stock_disponible < cantidad:
                        raise Exception(f"Stock insuficiente para el producto con ID {producto_id}")
                    
                    detalles_values.append((venta_id, producto_id, cantidad))
                    stock_updates.append((cantidad, producto_id))

                # 5. Batch insert detalle_ventas
                cursor.executemany('''
                    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad) 
                    VALUES (%s, %s, %s)
                ''', detalles_values)

                # 6. Batch update stock
                cursor.executemany('''
                    UPDATE productos 
                    SET disponible = CAST(disponible - %s AS DECIMAL(10,3)) 
                    WHERE id = %s
                ''', stock_updates)

                # 7. Insert deuda if needed
                if metodo_pago == "A Crédito" and cliente_id is not None:
                    cursor.execute('''
                        INSERT INTO deudas (cliente_id, venta_id, fecha, monto) 
                        VALUES (%s, %s, CURRENT_TIMESTAMP, %s)
                    ''', (cliente_id, venta_id, total))

                conn.commit()
                signals.venta_realizada.emit()
                return True, venta_id

            except Exception as e:
                conn.rollback()
                print("Error al registrar venta:", e)
                return False, None
            
            
#Caja

def obtener_detalle_ventas(venta_id):
    """Get sale details using connection context manager"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT p.nombre, dv.cantidad 
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                WHERE dv.venta_id = %s
            ''', (venta_id,))
            detalles = cursor.fetchall()
    
    # Format details string
    detalles_texto = "; ".join(
        f"{nombre} (x{cantidad:.2f} kg)" if isinstance(cantidad, float) and not cantidad.is_integer() 
        else f"{nombre} (x{int(cantidad)})"
        for nombre, cantidad in detalles
    )
    return detalles_texto

def obtener_detalle_ventas1(venta_id):
    """Get detailed sale information using connection context manager"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT p.nombre, dv.cantidad, p.precio_costo, p.precio_venta 
                FROM detalle_ventas dv
                JOIN productos p ON dv.producto_id = p.id
                WHERE dv.venta_id = %s
            ''', (venta_id,))
            return cursor.fetchall()
        
def obtener_ventas_por_dia(fecha):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
                FROM ventas v
                WHERE date(v.fecha) = %s AND v.metodo_pago != 'Pago de deuda'
            ''', (fecha,))
            ventas = cursor.fetchall()

    # Process sales outside the connection context
    ventas_con_detalle = []
    for venta in ventas:
        fecha_str, monto_total, metodo_pago, venta_id = venta
        
        # Convert datetime to string if it's a datetime object
        if isinstance(fecha_str, datetime):
            fecha_formateada = fecha_str.strftime("%d/%m/%Y %H:%M")
        else:
            # If it's already a string, parse it
            try:
                if " " in str(fecha_str):
                    fecha_obj = datetime.strptime(str(fecha_str), "%Y-%m-%d %H:%M:%S")
                else:
                    fecha_obj = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                # Fallback format if parsing fails
                fecha_formateada = str(fecha_str)
        
        detalle = obtener_detalle_ventas1(venta_id)
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)
        ventas_con_detalle.append((fecha_formateada, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle

def obtener_ventas_por_periodo(fecha_inicio, fecha_fin):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT v.fecha, v.monto_total, v.metodo_pago, v.id 
                FROM ventas v
                WHERE date(v.fecha) BETWEEN %s AND %s AND v.metodo_pago != 'Pago de deuda'
            ''', (fecha_inicio, fecha_fin))
            ventas = cursor.fetchall()

    # Process sales outside the connection context
    ventas_con_detalle = []
    for venta in ventas:
        fecha_str, monto_total, metodo_pago, venta_id = venta
        
        # Convert datetime to string if it's a datetime object
        if isinstance(fecha_str, datetime):
            fecha_formateada = fecha_str.strftime("%d/%m/%Y %H:%M")
        else:
            # If it's already a string, parse it
            try:
                if " " in str(fecha_str):
                    fecha_obj = datetime.strptime(str(fecha_str), "%Y-%m-%d %H:%M:%S")
                else:
                    fecha_obj = datetime.strptime(str(fecha_str), "%Y-%m-%d")
                fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                # Fallback format if parsing fails
                fecha_formateada = str(fecha_str)
        
        detalle = obtener_detalle_ventas1(venta_id)
        ganancia = sum((item[3] - item[2]) * item[1] for item in detalle)
        
        ventas_con_detalle.append((fecha_formateada, monto_total, metodo_pago, detalle, ganancia))
    
    return ventas_con_detalle

def obtener_total_ventas_efectivo(fecha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(monto_total) FROM ventas WHERE fecha = %s AND metodo_pago = 'Efectivo'
    ''', (fecha,))
    total_efectivo = cursor.fetchone()[0] or 0  # Si no hay ventas, devuelve 0
    conn.close()
    return total_efectivo        


#Clientes

def agregar_cliente_a_db(nombre):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("INSERT INTO clientes (nombre) VALUES (%s) RETURNING id", (nombre,))
                cliente_id = cursor.fetchone()[0]
                conn.commit()
                signals.cliente_agregado.emit()
                return True, cliente_id
            except Exception as e:
                conn.rollback()
                print(f"Error al agregar cliente: {e}")
                return False, None

def obtener_clientes():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT c.id, c.nombre,
                           COALESCE(SUM(d.monto), 0) as deuda_total,
                           COALESCE(SUM(p.monto), 0) as total_pagado
                    FROM clientes c
                    LEFT JOIN deudas d ON c.id = d.cliente_id
                    LEFT JOIN pagos p ON c.id = p.cliente_id
                    GROUP BY c.id, c.nombre
                    ORDER BY c.nombre
                """)
                return [
                    {
                        "id": row[0],
                        "nombre": row[1],
                        "deuda_total": float(row[2]),
                        "total_pagado": float(row[3])
                    } for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error al obtener clientes: {e}")
                return []

def obtener_deudas_cliente(cliente_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT d.fecha, d.monto, d.venta_id,
                           COALESCE(SUM(p.monto), 0) as monto_pagado
                    FROM deudas d
                    LEFT JOIN pagos p ON d.venta_id = p.venta_id
                    WHERE d.cliente_id = %s
                    GROUP BY d.id, d.fecha, d.monto, d.venta_id
                    ORDER BY d.fecha DESC
                """, (cliente_id,))
                
                return [
                    {
                        "fecha": row[0],
                        "monto_total": float(row[1]),
                        "venta_id": row[2],
                        "monto_pagado": float(row[3]),
                        "monto_pendiente": float(row[1]) - float(row[3])
                    } for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error al obtener deudas: {e}")
                return []

def obtener_pagos_cliente(cliente_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT p.fecha, p.monto, p.venta_id,
                           v.monto_total as monto_venta_total,
                           COALESCE(d.monto, 0) as deuda_original
                    FROM pagos p
                    LEFT JOIN ventas v ON p.venta_id = v.id
                    LEFT JOIN deudas d ON p.venta_id = d.venta_id
                    WHERE p.cliente_id = %s
                    ORDER BY p.fecha DESC
                """, (cliente_id,))
                
                return [
                    {
                        "fecha": row[0],
                        "monto_pagado": float(row[1]),
                        "venta_id": row[2],
                        "monto_venta_total": float(row[3]) if row[3] else 0,
                        "deuda_original": float(row[4])
                    } for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error al obtener pagos: {e}")
                return []
            
            
def obtener_detalle_ventas_deudas(cliente_id):
    """Obtiene las deudas de un cliente con el detalle completo de las ventas."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Single query to get all necessary information
                cursor.execute("""
                    SELECT 
                        d.fecha,
                        d.monto,
                        d.venta_id,
                        v.monto_total,
                        COALESCE(SUM(p.monto), 0) as monto_pagado,
                        json_agg(
                            json_build_object(
                                'nombre', COALESCE(pr.nombre, 'Producto Desconocido'),
                                'cantidad', dv.cantidad,
                                'precio_unitario', pr.precio_venta
                            )
                        ) as detalles
                    FROM deudas d
                    JOIN ventas v ON d.venta_id = v.id
                    LEFT JOIN detalle_ventas dv ON v.id = dv.venta_id
                    LEFT JOIN productos pr ON dv.producto_id = pr.id
                    LEFT JOIN pagos p ON d.venta_id = p.venta_id
                    WHERE d.cliente_id = %s
                    GROUP BY d.fecha, d.monto, d.venta_id, v.monto_total
                    ORDER BY d.fecha DESC
                """, (cliente_id,))
                
                return [
                    {
                        "fecha": row[0],
                        "monto": float(row[1]),
                        "monto_total": float(row[3]),
                        "monto_pagado": float(row[4]),
                        "venta_id": row[2],
                        "detalle": row[5] if row[5] else []
                    }
                    for row in cursor.fetchall()
                ]
            except Exception as e:
                print(f"Error al obtener detalles de ventas: {e}")
                return []

def registrar_pago_cliente(cliente_id, monto):
    """Registra el pago de un cliente y actualiza sus deudas."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Begin transaction
                cursor.execute("BEGIN")
                
                # Get all unpaid debts in one query
                cursor.execute("""
                    WITH DeudaPendiente AS (
                        SELECT 
                            d.id,
                            d.venta_id,
                            d.monto as monto_original,
                            d.monto - COALESCE(SUM(p.monto), 0) as monto_pendiente
                        FROM deudas d
                        LEFT JOIN pagos p ON d.venta_id = p.venta_id
                        WHERE d.cliente_id = %s
                        GROUP BY d.id, d.venta_id, d.monto
                        HAVING d.monto > COALESCE(SUM(p.monto), 0)
                        ORDER BY d.fecha ASC
                        FOR UPDATE
                    )
                    SELECT * FROM DeudaPendiente
                """, (cliente_id,))
                
                deudas = cursor.fetchall()
                
                if not deudas:
                    raise Exception("El cliente no tiene deudas pendientes.")
                
                monto_restante = monto
                pagos_a_registrar = []
                deudas_a_actualizar = []
                deudas_a_eliminar = []
                
                # Process all debts
                for deuda_id, venta_id, monto_original, monto_pendiente in deudas:
                    if monto_restante <= 0:
                        break
                        
                    pago_actual = min(monto_restante, monto_pendiente)
                    monto_restante -= pago_actual
                    
                    pagos_a_registrar.append((
                        cliente_id,
                        venta_id,
                        pago_actual
                    ))
                    
                    if pago_actual >= monto_pendiente:
                        deudas_a_eliminar.append(deuda_id)
                    else:
                        deudas_a_actualizar.append((
                            monto_original - pago_actual,
                            deuda_id
                        ))
                
                # Batch insert payments
                if pagos_a_registrar:
                    cursor.executemany("""
                        INSERT INTO pagos (cliente_id, venta_id, monto, fecha)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """, pagos_a_registrar)
                
                # Batch update remaining debts
                if deudas_a_actualizar:
                    cursor.executemany("""
                        UPDATE deudas SET monto = %s WHERE id = %s
                    """, deudas_a_actualizar)
                
                # Batch delete fully paid debts
                if deudas_a_eliminar:
                    cursor.execute("""
                        DELETE FROM deudas WHERE id = ANY(%s)
                    """, (deudas_a_eliminar,))
                
                cursor.execute("COMMIT")
                return True
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                print(f"Error al registrar pago: {e}")
                return False
            
            
# Usuarios

def hash_password(password):
    """Convierte la contraseña en un hash seguro."""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_credenciales(nombre_usuario, password):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Store the timestamp directly in local time without timezone conversion
                cursor.execute('''
                    UPDATE usuarios 
                    SET ultima_conexion = (NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires')
                    WHERE nombre = %s AND contrasena = %s 
                    RETURNING rol
                ''', (nombre_usuario, hash_password(password)))
                
                resultado = cursor.fetchone()
                if resultado:
                    conn.commit()
                    return True, resultado[0]
                return False, None
            except Exception as e:
                print(f"Error en verificación de credenciales: {e}")
                return False, None
            
def registrar_desconexion(nombre_usuario):
    """Register user disconnection using connection context manager"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Store the timestamp directly in local time without timezone conversion
            cursor.execute('''
                UPDATE usuarios
                SET ultima_desconexion = (NOW() AT TIME ZONE 'America/Argentina/Buenos_Aires')
                WHERE nombre = %s
            ''', (nombre_usuario,))
            conn.commit()
                    
def crear_usuario_admin_default():
    """Creates a default admin user if no users exist in the system."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Check if any user exists using COUNT optimization
                cursor.execute('''
                    SELECT EXISTS (
                        SELECT 1 FROM usuarios LIMIT 1
                    )
                ''')
                
                if not cursor.fetchone()[0]:
                    # Get current timestamp in Argentina timezone
                    argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
                    fecha_actual = datetime.now(argentina_tz)
                    
                    # Create default admin user with prepared statement
                    cursor.execute(''' 
                        INSERT INTO usuarios 
                            (nombre, contrasena, rol, ultima_conexion)
                        VALUES 
                            (%s, %s, %s, %s)
                        ON CONFLICT (nombre) DO NOTHING
                        RETURNING id
                    ''', (
                        'admin',
                        hash_password('admin123'),
                        'administrador',
                        fecha_actual
                    ))
                    
                    if cursor.fetchone():
                        conn.commit()
                        print("Default admin user created successfully")
                        return True
                    
                return False
                
            except Exception as e:
                conn.rollback()
                print(f"Error creating default admin user: {e}")
                return False
                                   
def crear_usuario(nombre, password, rol):
    """Crea un nuevo usuario."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO usuarios (nombre, contrasena, rol)
                    VALUES (%s, %s, %s)
                    RETURNING id
                ''', (nombre, hash_password(password), rol))
                usuario_id = cursor.fetchone()[0]
                conn.commit()
                return True, usuario_id
            except Exception as e:
                conn.rollback()
                print(f"Error al crear usuario: {e}")
                return False, None

def modificar_usuario(id_usuario, nuevo_nombre, password, rol):
    """Modifica un usuario existente usando su ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                if password:
                    cursor.execute('''
                        UPDATE usuarios
                        SET nombre = %s, 
                            contrasena = %s, 
                            rol = %s
                        WHERE id = %s
                        RETURNING id
                    ''', (nuevo_nombre, hash_password(password), rol, id_usuario))
                else:
                    cursor.execute('''
                        UPDATE usuarios
                        SET nombre = %s, 
                            rol = %s
                        WHERE id = %s
                        RETURNING id
                    ''', (nuevo_nombre, rol, id_usuario))
                
                if cursor.fetchone() is None:
                    raise Exception("Usuario no encontrado")
                    
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error al modificar usuario: {e}")
                return False

def obtener_modificaciones():
    """Obtiene el historial de modificaciones con detalles optimizados."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    SELECT 
                        m.id,
                        m.usuario,
                        m.fecha_hora,
                        m.tipo_modificacion,
                        COALESCE(p.nombre, '[Producto Eliminado]') as producto_nombre,
                        m.campo_modificado,
                        m.valor_anterior,
                        m.valor_nuevo
                    FROM modificaciones m
                    LEFT JOIN productos p ON m.producto_id = p.id
                    ORDER BY m.fecha_hora DESC
                    LIMIT 1000
                ''')
                
                return [
                    {
                        'id': row[0],
                        'usuario': row[1],
                        'fecha_hora': row[2],
                        'tipo_modificacion': row[3],
                        'producto_nombre': row[4],
                        'campo_modificado': row[5],
                        'valor_anterior': row[6],
                        'valor_nuevo': row[7]
                    }
                    for row in cursor.fetchall()
                ]
            
            except Exception as e:
                print(f"Error al obtener modificaciones: {e}")
                return []

def obtener_usuarios():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, rol, ultima_conexion, ultima_desconexion
                FROM usuarios
                ORDER BY nombre ASC
            """)
            
            return [
                {
                    "id": row[0],
                    "nombre": row[1],
                    "rol": row[2],
                    "ultima_conexion": row[3],
                    "ultima_desconexion": row[4]
                }
                for row in cursor.fetchall()
            ]
                        
def eliminar_usuario(usuario_id):
    """Elimina un usuario de la base de datos por su ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    DELETE FROM usuarios
                    WHERE id = %s
                    RETURNING id
                """, (usuario_id,))
                
                if cursor.fetchone() is None:
                    return False
                
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error al eliminar usuario: {e}")
                return False
            
def actualizar_estado_usuarios():
    """Actualiza el estado de conexión de los usuarios en la base de datos."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Obtener la fecha y hora actual en la zona horaria de Argentina
                argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
                ahora = datetime.now(argentina_tz)

                # Actualizar el estado de conexión
                cursor.execute('''
                    UPDATE usuarios
                    SET ultima_conexion = CURRENT_TIMESTAMP AT TIME ZONE 'America/Argentina/Buenos_Aires'
                    WHERE ultima_conexion > ultima_desconexion
                ''')
                
                conn.commit()
                print("Estado de conexión de los usuarios actualizado.")
            except Exception as e:
                print(f"Error al actualizar el estado de los usuarios: {e}")
                
def modificar_columna_detalle_ventas():
    """Modifica la columna 'cantidad' de la tabla 'detalle_ventas' a tipo REAL."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('''
                    ALTER TABLE detalle_ventas
                    ALTER COLUMN cantidad TYPE REAL USING cantidad::REAL;
                ''')
                conn.commit()
                print("Columna 'cantidad' modificada a tipo REAL en 'detalle_ventas'.")
            except Exception as e:
                conn.rollback()
                print(f"Error al modificar la columna: {e}")