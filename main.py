import sys
import uuid
import os
import platform
import subprocess
import hashlib
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget, QDialog, QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import QFile, QTextStream, Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon
from backup import create_backup_if_needed
from productos_tab import ProductosTab
from usuarios_tab import UsuariosTab
from ventas_tab import VentasTab
from caja_tab import CajaTab
from etiquetas_tab import EtiquetasTab 
from config_postgres import get_db_config
from db_postgres import crear_tablas, crear_indices, logger, optimizar_base_datos, crear_usuario_admin_default, registrar_desconexion, connection_pool  # Asegurarnos de que las tablas estén creadas
from login_window import LoginWindow
from modificaciones_tab import ModificacionesTab

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión")
        self.setWindowIcon(QIcon("stock.ico"))  # Establecer el icono de la ventana
        self.rol_usuario = None
        self.nombre_usuario = None
        self.barra_superior = None
        
        # Usar un QStackedWidget para manejar el login y la pantalla principal
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Agregar la pantalla de login
        self.login_window = LoginWindow(self)
        self.stacked_widget.addWidget(self.login_window)

        # Inicializar la pantalla principal (pero no mostrarla aún)
        self.main_widget = QWidget()
        self.init_ui()  # Inicializa la UI sin pestañas
        self.stacked_widget.addWidget(self.main_widget)

        # Mostrar la pantalla de login inicialmente
        self.stacked_widget.setCurrentIndex(0)

        # Conectar la señal de login exitoso
        self.login_window.login_exitoso.connect(self.mostrar_pantalla_principal)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                height: 40px;  /* Aumentar altura */
                width: 150px;  /* Aumentar ancho */
            }
            QTabBar::tab:selected {
                background-color: #4A4A4A;  /* Color más oscuro para la pestaña seleccionada */
                color: white;  /* Cambiar el color del texto */
            }
        """)
        # No agregar pestañas aquí, lo haremos después del login

    def setup_barra_usuario(self):
        if self.barra_superior is not None:
            self.barra_superior.deleteLater()
        # Crear widget para la barra superior
        barra_superior = QWidget()
        barra_superior.setObjectName("barraSuperior")
        layout_barra = QHBoxLayout()
        layout_barra.setContentsMargins(10, 5, 10, 5)
        
        # Contenedor para el nombre de usuario (izquierda)
        container_usuario = QWidget()
        container_usuario.setObjectName("containerUsuario")
        layout_usuario = QHBoxLayout()
        layout_usuario.setContentsMargins(0, 0, 0, 0)
        
        # Icono de usuario
        icono_usuario = QLabel("👤")
        icono_usuario.setObjectName("iconoUsuario")
        layout_usuario.addWidget(icono_usuario)
        
        # Etiqueta con el nombre de usuario
        label_usuario = QLabel(self.nombre_usuario)
        label_usuario.setObjectName("etiquetaUsuario")
        layout_usuario.addWidget(label_usuario)
        
        container_usuario.setLayout(layout_usuario)
        layout_barra.addWidget(container_usuario)
        
        # Espacio flexible izquierdo
        layout_barra.addStretch(1)
        
        # Contenedor para el logo (centro)
        container_logo = QWidget()
        container_logo.setObjectName("containerLogo")
        layout_logo = QHBoxLayout()
        layout_logo.setContentsMargins(0, 0, 0, 0)
        
        # Logo
        logo_label = QLabel()
        logo_label.setObjectName("logoBarraSuperior")
        logo_pixmap = QPixmap(resource_path("lisintac.png"))
        # Escalar el logo para que se ajuste a la altura de la barra
        scaled_pixmap = logo_pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_logo.addWidget(logo_label)
        
        container_logo.setLayout(layout_logo)
        layout_barra.addWidget(container_logo)
        
        # Espacio flexible derecho
        layout_barra.addStretch(1)
        
        # Botones de la derecha
        botones_container = QWidget()
        botones_layout = QHBoxLayout()
        botones_layout.setContentsMargins(0, 0, 0, 0)
        
        # Botón de desconexión
        btn_desconectar = QPushButton("Desconectar")
        btn_desconectar.setObjectName("botonDesconectar")
        btn_desconectar.setToolTip("Desconectar")
        btn_desconectar.clicked.connect(self.logout)
        botones_layout.addWidget(btn_desconectar)
        
        botones_container.setLayout(botones_layout)
        layout_barra.addWidget(botones_container)
        
        barra_superior.setLayout(layout_barra)
        
        # Agregar la barra superior al layout principal
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(0)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addWidget(barra_superior)
        layout_principal.addWidget(self.tabs)
        
        # Widget central
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        
        # Clear existing layout if any
        if self.main_widget.layout():
            while self.main_widget.layout().count():
                child = self.main_widget.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            self.main_widget.setLayout(QVBoxLayout())
            
        self.main_widget.layout().addWidget(widget_central)
            
    def logout(self):
        registrar_desconexion(self.nombre_usuario)
        
        # Limpiar la información del usuario actual
        self.nombre_usuario = None
        self.rol_usuario = None
        
        # Limpiar y eliminar las pestañas actuales
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        
         # Clear the user bar
        if self.barra_superior is not None:
            self.barra_superior.deleteLater()
            self.barra_superior = None
        
        self.login_window.clear_inputs()
        # Mostrar la ventana de login
        self.stacked_widget.setCurrentIndex(0)
            
    def closeEvent(self, event):
        registrar_desconexion(self.nombre_usuario)
        if 'connection_pool' in globals():
            connection_pool.closeall()
        event.accept()


    def cargar_estilos(self):
        # Obtener la ruta base de la aplicación
        if getattr(sys, 'frozen', False):
            # Si es un ejecutable
            application_path = sys._MEIPASS
        else:
            # Si es el script Python
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        # Construir la ruta completa al archivo de estilos
        qss_path = os.path.join(application_path, 'styles.qss')
        
        archivo_qss = QFile(qss_path)
        if archivo_qss.open(QFile.OpenModeFlag.ReadOnly):
            stream = QTextStream(archivo_qss)
            self.app.setStyleSheet(stream.readAll())
        else:
            print(f"No se pudo cargar el archivo QSS desde: {qss_path}")
            
    def mostrar_pantalla_principal(self, nombre_usuario, rol_usuario):
        self.nombre_usuario = nombre_usuario
        self.rol_usuario = rol_usuario

        # Keep the spinner visible during the entire loading process
        self.login_window.spinner_label.show()
        self.login_window.spinner_movie.start()
        self.login_window.boton_login.setEnabled(False)
        
        # Create tabs in chunks to keep UI responsive
        QTimer.singleShot(100, self._setup_pantalla_principal_parte1)

    def _setup_pantalla_principal_parte1(self):
        self.login_window.spinner_movie.start()
        # First part: Create basic structure
        if self.rol_usuario == 'administrador':
            self.tabs.addTab(ProductosTab(self.nombre_usuario), "Productos")
            QTimer.singleShot(100, self._setup_pantalla_principal_parte2)
        elif self.rol_usuario == 'empleado':
            self.tabs.addTab(ProductosTab(self.nombre_usuario), "Productos")
            QTimer.singleShot(100, self._setup_pantalla_principal_parte2)

    def _setup_pantalla_principal_parte2(self):
        self.login_window.spinner_movie.start()
        # Second part: Add more tabs
        if self.rol_usuario == 'administrador':
            self.tabs.addTab(VentasTab(), "Ventas")
            self.tabs.addTab(CajaTab(), "Caja")
            self.tabs.addTab(EtiquetasTab(), "Etiquetas")  # Agregar la pestaña de etiquetas
            QTimer.singleShot(100, self._setup_pantalla_principal_parte3)
        elif self.rol_usuario == 'empleado':
            self.tabs.addTab(VentasTab(), "Ventas")
            self.tabs.addTab(EtiquetasTab(), "Etiquetas")
            QTimer.singleShot(100, self._finalizar_setup)

    def _setup_pantalla_principal_parte3(self):
        self.login_window.spinner_movie.start()
        # Third part: Add remaining tabs for admin
        self.tabs.addTab(UsuariosTab(self.nombre_usuario), "Usuarios")
        self.tabs.addTab(ModificacionesTab(), "Modificaciones")
        QTimer.singleShot(100, self._finalizar_setup)

    def _finalizar_setup(self):
        # Final setup==
        self.setup_barra_usuario()
        self.stacked_widget.setCurrentIndex(1)
        
        # Only stop the spinner after the UI is fully visible
        QTimer.singleShot(300, self._finalizar_login)
                        
    def _finalizar_login(self):
        # Hide login window spinner
        self.login_window.spinner_movie.stop()
        self.login_window.spinner_label.hide()
        self.login_window.boton_login.setEnabled(True)
        
def realizar_tareas_cierre():
    """Función para realizar tareas antes de cerrar la aplicación"""
    try:
        create_backup_if_needed()  # Crear backup si es necesario
    except Exception as e:
        print(f"Error al realizar tareas de cierre: {e}")
        
def obtener_hardware_id():
    """Genera un ID de hardware único basado en múltiples componentes del sistema"""
    # Obtener información del sistema
    system_info = platform.uname()
    
    # Obtener número de serie del disco duro en Windows
    disk_serial = ""
    try:
        if platform.system() == "Windows":
            # Usar PowerShell en lugar de wmic
            output = subprocess.check_output("powershell -Command \"Get-PhysicalDisk | Select-Object SerialNumber | Format-List\"", shell=True).decode().strip()
            if "SerialNumber" in output:
                disk_serial = output.split("SerialNumber:", 1)[1].strip()
    except:
        disk_serial = "unknown_disk"
    
    # Obtener CPU ID
    cpu_info = ""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("powershell -Command \"Get-WmiObject -Class Win32_Processor | Select-Object ProcessorId | Format-List\"", shell=True).decode().strip()
            if "ProcessorId" in output:
                cpu_info = output.split("ProcessorId:", 1)[1].strip()
    except:
        cpu_info = "unknown_cpu"
    
    # Obtener información de la placa base
    motherboard_info = ""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("powershell -Command \"Get-WmiObject -Class Win32_BaseBoard | Select-Object SerialNumber | Format-List\"", shell=True).decode().strip()
            if "SerialNumber" in output:
                motherboard_info = output.split("SerialNumber:", 1)[1].strip()
    except:
        motherboard_info = "unknown_motherboard"
    
    # Combinar toda la información
    hardware_components = [
        system_info.node,  # Nombre del equipo
        system_info.machine,  # Arquitectura
        disk_serial,
        cpu_info,
        motherboard_info,
        str(uuid.getnode())  # MAC address como respaldo
    ]
    
    # Crear un hash único a partir de los componentes
    fingerprint = hashlib.sha256(":".join(hardware_components).encode()).hexdigest()
    
    return fingerprint

def verificar_licencia():
    """Verifica si la aplicación se está ejecutando en la PC autorizada usando un ID de hardware más estable."""
    # Obtener el ID de hardware actual
    hardware_id_actual = obtener_hardware_id()
    
    # Lista de IDs de hardware autorizados (puedes agregar más si es necesario)
    hardware_ids_autorizados = [
        "8b2db4d14411",  # ID antiguo basado en MAC (para compatibilidad)
        # Reemplaza este valor con el hash generado por obtener_hardware_id()
        "b7b45cde6b091ddaa6e9438932bcf4e262119406c9bf31e3368dfd355b80ee5e",  # Ejemplo de ID de hardware
        hardware_id_actual
    ]
    
    # Verificar si el ID actual está en la lista de autorizados
    if not any(id_auth in hardware_id_actual for id_auth in hardware_ids_autorizados):
        # Para depuración, mostrar el ID actual
        print(f"ID de Hardware actual: {hardware_id_actual}")
        QMessageBox.critical(None, "Licencia no válida", 
                            "Este programa solo puede ejecutarse en una PC autorizada.\n\n"
                            "ID de Hardware: " + hardware_id_actual[:16] + "...")
        sys.exit(1)  # Salir si la licencia no es válida

def initialize_database():
    """Initialize database with tables and indexes"""
    logger.info("Iniciando creación de tablas...")
    crear_tablas()
    logger.info("Tablas creadas correctamente")
    
    logger.info("Creando índices...")
    crear_indices()
    logger.info("Índices creados correctamente")
    
    # Optimizar base de datos en segundo plano para no bloquear la UI
    QTimer.singleShot(1000, optimizar_base_datos)
    
    logger.info("Base de datos inicializada")

    
if __name__ == "__main__":
    app = QApplication(sys.argv)  # Crear la instancia de QApplication primero
    verificar_licencia()  # Verificar la licencia después de crear QApplication
    initialize_database()
    crear_usuario_admin_default()  # Crear el usuario admin por defecto si no existe
    
    main_window = MainWindow()  # Crear la ventana principal
    main_window.app = app
    main_window.cargar_estilos()
    app.aboutToQuit.connect(realizar_tareas_cierre)
    main_window.showMaximized()
    sys.exit(app.exec())
