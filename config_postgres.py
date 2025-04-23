import os

# Configuración para producción o Railway
LOCAL_MODE = False

DB_CONFIG = {
    "host": "switchback.proxy.rlwy.net",
    "database": "railway",
    "user": "postgres",
    "password": "vPBwFiAJJsSxmCbrXvZMumPTvGrnQsoq",
    "port": "16336"                # Generalmente 5432 o el asignado por Railway
}

def get_db_config():
    return DB_CONFIG
