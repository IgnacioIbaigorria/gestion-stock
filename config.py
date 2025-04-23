import os
import sqlite3

# Configuración para desarrollo local
LOCAL_MODE = False

# Rutas de las bases de datos
LOCAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dietetica.db')
NETWORK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'network', 'dietetica.db')

# Tiempo máximo (en segundos) para intentar sincronizar
SYNC_TIMEOUT = 5

def get_db_path():
    """Obtener la ruta de la base de datos"""
    return LOCAL_PATH

def init_database():
    """Inicializar la base de datos si no existe"""
    if not os.path.exists(LOCAL_PATH):
        conn = sqlite3.connect(LOCAL_PATH)
        conn.close()