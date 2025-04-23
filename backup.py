import os
import shutil
from datetime import datetime, timedelta

# Ruta de la base de datos
DB_PATH = "dietetica.db"

# Ruta de la carpeta de OneDrive
BACKUP_FOLDER = r"C:\Users\Backups"

# Archivo para registrar la última fecha de backup
LAST_BACKUP_FILE = "last_backup.txt"

def get_last_backup_date():
    """Obtiene la fecha del último backup desde el archivo de registro."""
    if os.path.exists(LAST_BACKUP_FILE):
        try:
            with open(LAST_BACKUP_FILE, "r") as f:
                contenido = f.read().strip()
                # Verificar si el contenido es un error
                if contenido.startswith("ERROR:"):
                    return None
                return datetime.strptime(contenido, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    return None

def set_last_backup_date(success=True, error_message=None):
    """
    Registra la fecha y hora actual como el último backup o el error si falló.
    
    Args:
        success (bool): True si el backup fue exitoso, False si hubo error
        error_message (str): Mensaje de error si success es False
    """
    with open(LAST_BACKUP_FILE, "w") as f:
        if success:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        else:
            f.write(f"ERROR: {error_message} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_backup():
    """Crea una copia de seguridad de la base de datos."""
    try:
        # Verificar que existe el archivo de base de datos
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"No se encuentra la base de datos en {DB_PATH}")

        # Crear carpeta de backup si no existe
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)

        # Nombre del archivo de backup con fecha y hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_FOLDER, f"backup_{timestamp}.db")

        # Copiar el archivo
        shutil.copy2(DB_PATH, backup_file)
        
        # Verificar que el archivo se copió correctamente
        if os.path.exists(backup_file):
            print(f"Copia de seguridad creada: {backup_file}")
            return True, None
        else:
            raise Exception("El archivo de backup no se creó correctamente")
            
    except Exception as e:
        error_msg = f"Error creando el backup: {str(e)}"
        print(error_msg)
        return False, error_msg

def create_backup_if_needed(days_interval=1):
    """Crea un backup si han pasado más de 'days_interval' días desde el último."""
    last_backup_date = get_last_backup_date()
    now = datetime.now()

    if not last_backup_date or (now - last_backup_date) >= timedelta(days=days_interval):
        print("Realizando backup...")
        success, error_message = create_backup()
        
        if success:
            set_last_backup_date(success=True)
            print("Backup completado exitosamente")
        else:
            set_last_backup_date(success=False, error_message=error_message)
            print(f"Error en el backup: {error_message}")
    else:
        print(f"No es necesario realizar backup. Último backup: {last_backup_date}")
