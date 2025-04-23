-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    contrasena TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('administrador', 'empleado')),
    ultima_conexion TIMESTAMP,
    ultima_desconexion TIMESTAMP
);

-- Tabla de clientes
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL
);

-- Tabla de productos
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo_barras TEXT,
    nombre TEXT,
    venta_por_peso INTEGER, -- 0 = por unidad, 1 = por peso
    disponible REAL,
    precio_costo REAL,
    precio_venta REAL,
    margen_ganancia REAL
);

-- Tabla de ventas
CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP,
    monto_total REAL,
    metodo_pago TEXT
);

-- Tabla detalle de ventas
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER,
    producto_id INTEGER,
    cantidad INTEGER,
    FOREIGN KEY(venta_id) REFERENCES ventas(id),
    FOREIGN KEY(producto_id) REFERENCES productos(id)
);

-- Tabla de deudas
CREATE TABLE IF NOT EXISTS deudas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    venta_id INTEGER NOT NULL,
    fecha TIMESTAMP NOT NULL,
    monto REAL NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (venta_id) REFERENCES ventas(id)
);


-- Tabla de pagos
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    fecha TIMESTAMP NOT NULL,
    monto REAL NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Tabla de modificaciones
CREATE TABLE IF NOT EXISTS modificaciones (
    id SERIAL PRIMARY KEY,
    usuario TEXT NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_modificacion TEXT NOT NULL,
    producto_id INTEGER,
    campo_modificado TEXT,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);
