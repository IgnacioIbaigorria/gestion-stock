-- Tabla para gestionar lotes de productos
CREATE TABLE IF NOT EXISTS lotes_productos (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL,
    peso_lote REAL NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disponible BOOLEAN DEFAULT TRUE,
    codigo_unico TEXT,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- Modificar la tabla detalle_ventas para incluir lotes

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_lotes_producto_id ON lotes_productos(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_disponible ON lotes_productos(disponible);
