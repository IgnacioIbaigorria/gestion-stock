import sqlite3

# Conectar a las bases de datos
conn_stock = sqlite3.connect('stock_management.db')
conn_kiosco = sqlite3.connect('kiosco_local.db')

# Crear cursores
cursor_stock = conn_stock.cursor()
cursor_kiosco = conn_kiosco.cursor()

# Obtener todos los datos de la tabla products
cursor_stock.execute("SELECT id, name, quantity, cost_price, profit_margin, price, barcode FROM products")
productos = cursor_stock.fetchall()

# Insertar los datos en la tabla productos de kiosco_local.db
for producto in productos:
    cursor_kiosco.execute("""
        INSERT INTO productos (id, codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (producto[0], producto[6], producto[1], 0, producto[2], producto[3], producto[5], producto[4]))

# Guardar cambios y cerrar conexiones
conn_kiosco.commit()
conn_stock.close()
conn_kiosco.close()

print("Datos copiados exitosamente.")