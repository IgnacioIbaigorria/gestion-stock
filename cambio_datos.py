import sqlite3
import os

# Conectar a las bases de datos
conn_stock_management = sqlite3.connect('stock_management.db')
conn_kiosco_local = sqlite3.connect('kiosco_local.db')

def copiar_productos(cursor_origen, cursor_destino):
    cursor_origen.execute("SELECT * FROM products")
    productos = cursor_origen.fetchall()

    # Insertar datos en la tabla productos de kiosco_local
    for producto in productos:
        # Asegúrate de que la cantidad de columnas coincida
        cursor_destino.execute('''
            INSERT INTO productos (nombre, disponible, precio_costo, margen_ganancia,  precio_venta, codigo_barras, venta_por_peso)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (producto[1], producto[2], producto[3], producto[4], producto[5], producto[6], 0))  # Asignar 0 a venta_por_peso

# Copiar productos
cursor_stock = conn_stock_management.cursor()
cursor_kiosco = conn_kiosco_local.cursor()
copiar_productos(cursor_stock, cursor_kiosco)

def copiar_ventas(cursor_origen, cursor_destino):
    cursor_origen.execute("SELECT * FROM sales_summary")
    ventas = cursor_origen.fetchall()

    # Insertar datos en la tabla ventas de kiosco_local
    for venta in ventas:
        cursor_destino.execute('''
            INSERT INTO ventas (monto_total, fecha, metodo_pago)
            VALUES (?, ?, ?)
        ''', (venta[1], venta[2], venta[3]))  # Asegúrate de que los índices coincidan con las columnas

# Copiar ventas
copiar_ventas(cursor_stock, cursor_kiosco)

def copiar_detalle_ventas(cursor_origen, cursor_destino):
    cursor_origen.execute("SELECT * FROM sales_details")
    detalles_ventas = cursor_origen.fetchall()

    # Insertar datos en la tabla detalle_ventas de kiosco_local
    for detalle in detalles_ventas:
        cursor_destino.execute('''
            INSERT INTO detalle_ventas (venta_id, producto_id, cantidad)
            VALUES (?, ?, ?)
        ''', (detalle[1], detalle[2], detalle[3]))  # Omitir el total

# Copiar detalle de ventas
copiar_detalle_ventas(cursor_stock, cursor_kiosco)

# Confirmar cambios
conn_kiosco_local.commit()

# Cerrar las conexiones
conn_stock_management.close()
conn_kiosco_local.close()