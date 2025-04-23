# login_window.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QMovie
from db_postgres import verificar_credenciales
from PyQt6.QtCore import pyqtSignal
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class LoginWindow(QDialog):
    login_exitoso = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar Sesión")
        self.setObjectName("loginWindow")
        self.setMinimumSize(400, 600)  # Reduced minimum size
        self.rol_usuario = None
        self.nombre_usuario = None
        self.setGeometry(100, 100, 400, 600)  # Adjusted initial size
        
        # Updated styles
        self.setStyleSheet("""
            #loginWindow {
                background-color: #f0f2f5;
            }
            
            #logoLabel {
                margin: 20px;
            }

            #loginForm {
                background-color: white;
                margin: 20px;
                padding: 30px;
                border-radius: 8px;
                border: 1px solid #ddd;
            }

            #loginButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                min-width: 200px;
                margin-top: 20px;
            }

            #loginButton:hover {
                background-color: #45a049;
            }

            #loginButton:pressed {
                background-color: #3d8b40;
            }

            #loginInput, #passwordInput {
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                margin: 8px 0;
                min-width: 150px;
            }

            #loginInput:focus, #passwordInput:focus {
                border: 2px solid #4CAF50;
                border-radius: 6px;
            }

            #loginLabel, #passwordLabel {
                font-size: 14px;
                color: #333;
                font-weight: bold;
                margin-top: 12px;
            }
        """)
        
        self.setup_ui()

    def setup_ui(self):
        # Layout principal with adjusted spacing
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Logo container with adjusted margins
        logo_container = QWidget()
        logo_container.setObjectName("logoContainer")
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(20, 20, 20, 10)
        
        # Logo
        logo_label = QLabel()
        logo_label.setObjectName("logoLabel")
        logo_pixmap = QPixmap(resource_path("lisintac.png"))
        scaled_pixmap = logo_pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo_label)
        
        logo_container.setLayout(logo_layout)
        layout.addWidget(logo_container)
        
        # Form container with adjusted spacing
        form_container = QWidget()
        form_container.setObjectName("loginForm")
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(40, 30, 40, 30)
                
        # Usuario
        self.label_usuario = QLabel("Usuario:")
        self.label_usuario.setObjectName("loginLabel")
        self.input_usuario = QLineEdit()
        self.input_usuario.setObjectName("loginInput")
        self.input_usuario.setPlaceholderText("Ingrese su usuario")
        form_layout.addWidget(self.label_usuario)
        form_layout.addWidget(self.input_usuario)
        
        # Contraseña
        self.label_password = QLabel("Contraseña:")
        self.label_password.setObjectName("passwordLabel")
        self.input_password = QLineEdit()
        self.input_password.setObjectName("passwordInput")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Ingrese su contraseña")
        form_layout.addWidget(self.label_password)
        form_layout.addWidget(self.input_password)
        
        # Botón de login
        self.boton_login = QPushButton("Iniciar Sesión")
        self.boton_login.setObjectName("loginButton")
        self.boton_login.clicked.connect(self.verificar_login)
        form_layout.addWidget(self.boton_login, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Spinner animado
        self.spinner_label = QLabel()
        self.spinner_movie = QMovie(resource_path("spinner.gif"))
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.hide()  # Ocultar inicialmente
        form_layout.addWidget(self.spinner_label)
        
        # Configurar el contenedor del formulario
        form_container.setLayout(form_layout)
        layout.addWidget(form_container)
        
        self.setLayout(layout)
        
        # Configurar Enter para iniciar sesión
        self.input_password.returnPressed.connect(self.verificar_login)
        self.input_usuario.returnPressed.connect(lambda: self.input_password.setFocus())
        
    def verificar_login(self):
        usuario = self.input_usuario.text()
        password = self.input_password.text()
        
        if not usuario or not password:
            QMessageBox.warning(self, "Error", "Por favor complete todos los campos")
            return
        
        # Mostrar el spinner
        self.spinner_movie.start()
        self.spinner_label.show()
        self.boton_login.setEnabled(False)  # Deshabilitar el botón de login
        
        # Usar un QTimer para simular un retraso (o procesar el login en segundo plano)
        QTimer.singleShot(1000, lambda: self.procesar_login(usuario, password))  # Simula un retraso de 1 segundo
        
    def procesar_login(self, usuario, password):
        exito, rol = verificar_credenciales(usuario, password)
        
        if exito:
            self.rol_usuario = rol
            self.nombre_usuario = usuario
            # Keep spinner visible and running
            self.spinner_movie.start()  # Ensure spinner is running
            self.spinner_label.show()
            self.login_exitoso.emit(self.nombre_usuario, self.rol_usuario)
        else:
            # Hide spinner and show error
            self.spinner_movie.stop()
            self.spinner_label.hide()
            self.boton_login.setEnabled(True)
            QMessageBox.warning(self, "Error", "Credenciales incorrectas")
            self.input_password.clear()
            self.input_password.setFocus()
                        
    def clear_inputs(self):
        """Clear login form inputs and reset UI state"""
        self.input_usuario.clear()
        self.input_password.clear()
        self.spinner_movie.stop()
        self.spinner_label.hide()
        self.boton_login.setEnabled(True)
        self.input_usuario.setFocus()