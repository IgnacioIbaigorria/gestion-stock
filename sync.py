import sqlite3
import os
import shutil
from datetime import datetime
from config import get_db_path
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

def get_table_names(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]

def get_last_modified(db_path):
    """Obtener la última fecha de modificación del archivo de base de datos"""
    return os.path.getmtime(db_path) if os.path.exists(db_path) else 0

class DatabaseSync:
    def __init__(self):
        self.setup_drive()
        
    def setup_drive(self):
        """Configura la autenticación con Google Drive"""
        try:
            self.gauth = GoogleAuth()
            # Usar credenciales guardadas o solicitar nuevas
            self.gauth.LoadCredentialsFile("mycreds.txt")
            if self.gauth.credentials is None:
                self.gauth.LocalWebserverAuth()
            elif self.gauth.access_token_expired:
                self.gauth.Refresh()
            else:
                self.gauth.Authorize()
            # Guardar credenciales
            self.gauth.SaveCredentialsFile("mycreds.txt")
            self.drive = GoogleDrive(self.gauth)
        except Exception as e:
            print(f"Error en la configuración de Drive: {e}")
            
    def upload_database(self):
        """Sube la base de datos a Google Drive"""
        try:
            # Buscar el archivo en Drive
            file_list = self.drive.ListFile({'q': "'root' in parents and title='dietetica.db'"}).GetList()
            
            if len(file_list) > 0:
                # Si existe, actualizarlo
                file = file_list[0]
                file.SetContentFile(get_db_path())
                file.Upload()
                print(f"Base de datos subida exitosamente")
                print(f"ID del archivo: {file['id']}")
                print(f"URL del archivo: https://drive.google.com/file/d/{file['id']}/view")
            else:
                # Si no existe, crear nuevo
                file = self.drive.CreateFile({'title': 'dietetica.db'})
                file.SetContentFile(get_db_path())
                file.Upload()
                print(f"Base de datos creada exitosamente")
                print(f"ID del archivo: {file['id']}")
                print(f"URL del archivo: https://drive.google.com/file/d/{file['id']}/view")
            
            return True
        except Exception as e:
            print(f"Error al subir la base de datos: {e}")
            return False
            
    def download_database(self):
        """Descarga la base de datos de Google Drive"""
        try:
            # Buscar el archivo en Drive
            file_list = self.drive.ListFile({'q': "'root' in parents and title='dietetica.db'"}).GetList()
            
            if len(file_list) > 0:
                file = file_list[0]
                # Crear backup de la base de datos local
                self.backup_local_database()
                # Descargar la nueva versión
                file.GetContentFile(get_db_path())
                print("Base de datos descargada exitosamente")
                return True
            else:
                print("No se encontró la base de datos en Drive")
                return False
        except Exception as e:
            print(f"Error al descargar la base de datos: {e}")
            return False
            
    def backup_local_database(self):
        """Crea una copia de seguridad de la base de datos local"""
        try:
            db_path = get_db_path()
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"dietetica_backup_{timestamp}.db")
            
            shutil.copy2(db_path, backup_path)
            print(f"Backup creado: {backup_path}")
            return True
        except Exception as e:
            print(f"Error al crear backup: {e}")
            return False
            
    def sync_databases(self):
        """Sincroniza las bases de datos local y remota"""
        try:
            # Primero descargar la versión más reciente
            if self.download_database():
                # Luego subir la versión actualizada
                self.upload_database()
                return True
            return False
        except Exception as e:
            print(f"Error en la sincronización: {e}")
            return False

    def get_drive_file_info(self):
        """Obtiene información sobre el archivo en Drive"""
        try:
            file_list = self.drive.ListFile({'q': "'root' in parents and title='dietetica.db'"}).GetList()
            if len(file_list) > 0:
                file = file_list[0]
                return {
                    'id': file['id'],
                    'title': file['title'],
                    'url': f"https://drive.google.com/file/d/{file['id']}/view",
                    'modified_date': file['modifiedDate']
                }
            return None
        except Exception as e:
            print(f"Error al obtener información del archivo: {e}")
            return None

def sync_to_local(source_conn, dest_conn):
    """Sincronizar desde la red hacia local"""
    tables = get_table_names(source_conn)
    
    for table in tables:
        # Ignorar la tabla sqlite_sequence
        if table == 'sqlite_sequence':
            continue
            
        try:
            # Obtener datos de la tabla de origen
            cursor = source_conn.cursor()
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Obtener estructura de la tabla
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            table_sql = cursor.fetchone()[0]
            
            # Recrear tabla en destino
            dest_conn.execute(f"DROP TABLE IF EXISTS {table}")
            dest_conn.execute(table_sql)
            
            # Insertar datos
            if rows:
                # Generar la sentencia INSERT
                placeholders = ','.join(['?' for _ in rows[0]])
                dest_conn.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})",
                    rows
                )
            
            dest_conn.commit()
            
        except Exception as e:
            print(f"Error sincronizando tabla {table}: {e}")
            dest_conn.rollback()

def sync_to_network(source_conn, dest_conn):
    """Sincronizar desde local hacia la red"""
    sync_to_local(source_conn, dest_conn)  # Usamos la misma lógica pero en dirección opuesta 