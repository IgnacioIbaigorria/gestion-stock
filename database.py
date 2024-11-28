import sqlite3

def connect_db():
    conn = sqlite3.connect('stock_management.db')
    c = conn.cursor()
    # Crear tablas si no existen
    c.execute('''CREATE TABLE IF NOT EXISTS products
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL,
                cost_price REAL NOT NULL,
                profit_margin REAL NOT NULL,
                price REAL NOT NULL,
                barcode TEXT NOT NULL
                            )''')
    # Crear tabla de ventas si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            date TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS sales_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL NOT NULL,
            date TEXT NOT NULL,
            payment_method TEXT NOT NULL
        )
    ''')

    c.execute('''
            CREATE TABLE IF NOT EXISTS sales_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales_summary(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')


    # Crear tabla de clientes si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    # Crear tabla de deudas si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            sale_id INTEGER,
            original_amount REAL NOT NULL,
            remaining_amount REAL NOT NULL,
            status TEXT DEFAULT 'pendiente',
            date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (sale_id) REFERENCES sales_summary (id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER,
            customer_id INTEGER,
            amount REAL,
            date TEXT,
            FOREIGN KEY(debt_id) REFERENCES debts(id),
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS cash_withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    # Más creación de tablas...
    conn.commit()
    return conn, c
