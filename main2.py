import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget, QDialog, QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtCore import QFile, QTextStream, Qt
from PyQt6.QtGui import QPixmap
from backup import create_backup_if_needed
from productos_tab import ProductosTab
from usuarios_tab import UsuariosTab
from ventas_tab import VentasTab
from caja_tab import CajaTab
from clientes_tab import ClientesTab
from config_postgres import get_db_config
from db_postgres import crear_tablas, crear_usuario_admin_default, registrar_desconexion  # Asegurarnos de que las tablas estén creadas
from login_window import LoginWindow
from modificaciones_tab import ModificacionesTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión")
        self.setGeometry(100, 100, 800, 600)
        self.rol_usuario = None
        self.nombre_usuario = None
        
        # No mostrar la ventana principal hasta que el login sea exitoso
        self.hide()  # Ocultar la ventana principal inicialmente
        if not self.login():  # Si el login falla, cerrar la aplicación
            sys.exit()
            
    def login(self):
        login_window = LoginWindow(self)

        # Establecer el login como ventana modal
        login_window.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        login_window.showMaximized()  # Mostrar correctamente

        if login_window.exec() == QDialog.DialogCode.Accepted:
            # Guardar el rol del usuario
            self.rol_usuario = login_window.rol_usuario
            self.nombre_usuario = login_window.nombre_usuario

            self.init_ui()

            self.showMaximized()  # Mostrar la ventana principal solo después de un login exitoso
            return True

        return False
            
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
        
        # Agregar pestañas según el rol del usuario
        if self.rol_usuario == 'administrador':
            # El administrador puede ver todas las pestañas
            self.tabs.addTab(ProductosTab(self.nombre_usuario), "Productos")
            self.tabs.addTab(VentasTab(), "Ventas")
            self.tabs.addTab(CajaTab(), "Caja")
            self.tabs.addTab(ClientesTab(), "Clientes")
            self.tabs.addTab(UsuariosTab(self.nombre_usuario), "Usuarios")
            self.tabs.addTab(ModificacionesTab(), "Modificaciones")
        elif self.rol_usuario == 'empleado':
            # El empleado solo puede ver Productos y Ventas
            self.tabs.addTab(ProductosTab(self.nombre_usuario), "Productos")
            self.tabs.addTab(VentasTab(), "Ventas")

        self.setup_barra_usuario()
        
    def setup_barra_usuario(self):
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
        logo_pixmap = QPixmap("lisintac.png")
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
        self.setCentralWidget(widget_central)
            
    def logout(self):
        registrar_desconexion(self.nombre_usuario)
        
        # Limpiar la información del usuario actual
        self.nombre_usuario = None
        self.rol_usuario = None
        
        # Limpiar y eliminar las pestañas actuales
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        
        # Ocultar la ventana principal
        self.hide()

        self.cargar_estilos()

        # Mostrar la ventana de login
        if not self.login():  # Si el login es exitoso
            sys.exit()
            
    def closeEvent(self, event):
        registrar_desconexion(self.nombre_usuario)
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
            
def realizar_tareas_cierre():
    """Función para realizar tareas antes de cerrar la aplicación"""
    try:
        create_backup_if_needed()  # Crear backup si es necesario
    except Exception as e:
        print(f"Error al realizar tareas de cierre: {e}")


if __name__ == "__main__":
    crear_usuario_admin_default()  # Crear el usuario admin por defecto si no existe
    
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.app = app
    main_window.cargar_estilos()
    app.aboutToQuit.connect(realizar_tareas_cierre)
    sys.exit(app.exec())
