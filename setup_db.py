import psycopg2
from config_postgres import get_db_config

# Obtener configuración
db_config = get_db_config()

# Leer el archivo init.sql
with open("init.sql", "r") as file:
    sql_script = file.read()

conn = None
cursor = None

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host=db_config["host"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"],
        port=db_config["port"]
    )
    cursor = conn.cursor()

    # Ejecutar el script
    cursor.execute(sql_script)
    conn.commit()
    print("🚀 Tablas creadas con éxito.")

except Exception as e:
    print("❌ Error al ejecutar el script:", e)

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
