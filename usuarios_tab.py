from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QDialog, QLineEdit,
                           QLabel, QComboBox, QMessageBox, QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer
from db_postgres import (obtener_usuarios, crear_usuario, eliminar_usuario, modificar_usuario, verificar_credenciales, registrar_desconexion)
from datetime import datetime
import pytz

class UsuariosTab(QWidget):
    def __init__(self, usuario_actual):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Botones superiores en un contenedor con alineación a la derecha
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # Esto empujará el botón hacia la derecha
        
        # Crear un contenedor para el botón
        btn_container = QWidget()
        btn_container.setObjectName("contenedorBotonUsuario")
        btn_container_layout = QHBoxLayout()
        btn_container_layout.setContentsMargins(0, 0, 0, 0)  # Eliminar márgenes
        
        self.btn_nuevo = QPushButton("+ Nuevo Usuario")  # Cambiar el texto
        self.btn_nuevo.setObjectName("agregarUsuarioCompacto")  # Nuevo estilo
        self.btn_nuevo.clicked.connect(self.mostrar_dialogo_nuevo_usuario)
        # Botón para actualizar usuarios
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("actualizarUsuarios")
        self.btn_actualizar.clicked.connect(self.cargar_usuarios)  # Llama al método para cargar usuarios
        
        btn_container_layout.addWidget(self.btn_nuevo)
        btn_container_layout.addWidget(self.btn_actualizar)  # Agregar el botón de actualización

        btn_container.setLayout(btn_container_layout)
        
        btn_layout.addWidget(btn_container)
        layout.addLayout(btn_layout)
        
        # Agregar un pequeño espacio entre el botón y la tabla
        layout.addSpacing(10)
        
        # Tabla de usuarios
        self.tabla_usuarios = QTableWidget()
        self.tabla_usuarios.setColumnCount(6)  # Aumentar el número de columnas
        
        # Ocultar los números de fila
        self.tabla_usuarios.verticalHeader().setVisible(False)
        
        # Restringir edición de celdas
        self.tabla_usuarios.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Ajustar el tamaño de las filas automáticamente
        self.tabla_usuarios.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Ajustar columnas
        self.tabla_usuarios.horizontalHeader().setStretchLastSection(True)
        self.tabla_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.tabla_usuarios.setHorizontalHeaderLabels([
            "En línea",  # Columna para el círculo de estado (sin nombre)
            "Usuario", "Rol", "Última Conexión", 
            "Última Desconexión", "Acciones"
        ])
        layout.addWidget(self.tabla_usuarios)
        
        self.setLayout(layout)
        self.cargar_usuarios()
        
    def cargar_usuarios(self):
    
        # Vaciar la tabla completamente
        self.tabla_usuarios.setRowCount(0)  # Borra todas las filas de la tabla
        self.btn_actualizar.setEnabled(False)  # Deshabilitar el botón de actualización

        # Configurar un temporizador para esperar 2 segundos antes de cargar los usuarios
        self.timer = QTimer()
        self.timer.setSingleShot(True)  # Solo se ejecuta una vez
        self.timer.timeout.connect(self.cargar_usuarios_despues_de_retraso)
        self.timer.start(1000)  # Esperar 2000 milisegundos (2 segundos)

        
    def cargar_usuarios_despues_de_retraso(self):
        usuarios = obtener_usuarios()
        self.tabla_usuarios.setRowCount(len(usuarios))
        
        # Define Argentina timezone
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')

        for i, usuario in enumerate(usuarios):
            # Crear un contenedor para el círculo de estado
            estado_container = QWidget()
            estado_layout = QHBoxLayout()
            estado_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Centrar el contenido
            estado_container.setLayout(estado_layout)
            
            # Crear un círculo de estado
            estado_label = QLabel()
            ultima_conexion = usuario['ultima_conexion']
            ultima_desconexion = usuario['ultima_desconexion']
            conectado = False
            
            if ultima_conexion and ultima_desconexion:
                # Comparar las fechas
                if ultima_conexion > ultima_desconexion:
                    conectado = True
            
            estado_color = "green" if conectado else "red"
            estado_label.setStyleSheet(f"background-color: {estado_color}; border-radius: 10px; width: 20px; height: 20px;")
            estado_label.setFixedSize(20, 20)
            
            estado_layout.addWidget(estado_label)  # Agregar el QLabel al layout centrado
            self.tabla_usuarios.setCellWidget(i, 0, estado_container)  # Colocar el contenedor en la celda
            
            # Mostrar el nombre del usuario en la siguiente columna
            self.tabla_usuarios.setItem(i, 1, QTableWidgetItem(usuario['nombre']))
            self.tabla_usuarios.setItem(i, 2, QTableWidgetItem(usuario['rol']))
            
            # Formatear última conexión
            ultima_conexion = usuario['ultima_conexion']
            if ultima_conexion:
                # The datetime is already in Argentina timezone from the database
                ultima_conexion_str = ultima_conexion.strftime('%d/%m/%Y %H:%M')
                self.tabla_usuarios.setItem(i, 3, QTableWidgetItem(ultima_conexion_str))
            else:
                self.tabla_usuarios.setItem(i, 3, QTableWidgetItem(''))

            # Formatear última desconexión
            ultima_desconexion = usuario['ultima_desconexion']
            if ultima_desconexion:
                # The datetime is already in Argentina timezone from the database
                ultima_desconexion_str = ultima_desconexion.strftime('%d/%m/%Y %H:%M')
                self.tabla_usuarios.setItem(i, 4, QTableWidgetItem(ultima_desconexion_str))
            else:
                self.tabla_usuarios.setItem(i, 4, QTableWidgetItem(''))
                        
            # Replace the separate buttons with a container
            acciones_container = QWidget()
            acciones_layout = QHBoxLayout()
            acciones_layout.setContentsMargins(0, 0, 0, 0)
            
            btn_modificar = QPushButton("Modificar")
            btn_modificar.setObjectName("modificarUsuario")
            btn_modificar.clicked.connect(lambda checked, u=usuario: self.mostrar_dialogo_modificar(u))
            
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setObjectName("eliminarUsuario")
            btn_eliminar.clicked.connect(lambda checked, u=usuario: self.confirmar_eliminar_usuario(u))
            
            acciones_layout.addWidget(btn_modificar)
            acciones_layout.addWidget(btn_eliminar)
            acciones_container.setLayout(acciones_layout)

            self.btn_actualizar.setEnabled(True)  # Habilitar el botón de actualización
            
            self.tabla_usuarios.setCellWidget(i, 5, acciones_container)
                
    def mostrar_dialogo_nuevo_usuario(self):
        dialogo = DialogoUsuario(self.usuario_actual, modo_nuevo=True)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
            
    def mostrar_dialogo_modificar(self, usuario):
        dialogo = DialogoUsuario(self.usuario_actual, usuario=usuario)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar_usuarios()
            
    def confirmar_eliminar_usuario(self, usuario):
        """Muestra un diálogo de confirmación antes de eliminar el usuario"""
        # Crear el mensaje de confirmación
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("Confirmar eliminación")
        mensaje.setText(f"¿Está seguro que desea eliminar el usuario {usuario['nombre']}?")
        mensaje.setIcon(QMessageBox.Icon.Question)
        
        # Crear botones en español
        boton_si = mensaje.addButton("Sí", QMessageBox.ButtonRole.YesRole)
        boton_no = mensaje.addButton("No", QMessageBox.ButtonRole.NoRole)
        mensaje.setDefaultButton(boton_no)  # Establecer "No" como opción predeterminada
        
        # Mostrar el diálogo y procesar la respuesta
        mensaje.exec()
        
        # Verificar qué botón se presionó
        if mensaje.clickedButton() == boton_si:
            eliminar_usuario(usuario)
            
class DialogoUsuario(QDialog):
    def __init__(self, usuario_actual, usuario=None, modo_nuevo=False):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.usuario = usuario
        self.modo_nuevo = modo_nuevo
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Campos del formulario
        self.input_usuario = QLineEdit()
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(['empleado', 'administrador'])
        
        # Contraseña del administrador actual
        self.input_admin_password = QLineEdit()
        self.input_admin_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        layout.addWidget(QLabel("Usuario:"))
        layout.addWidget(self.input_usuario)
        layout.addWidget(QLabel("Contraseña:"))
        layout.addWidget(self.input_password)
        if not self.modo_nuevo:
            layout.addWidget(QLabel("(Dejar en blanco para mantener la contraseña actual)"))
        layout.addWidget(QLabel("Rol:"))
        layout.addWidget(self.combo_rol)
        layout.addWidget(QLabel("Contraseña del administrador:"))
        layout.addWidget(self.input_admin_password)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_cancelar = QPushButton("Cancelar")
        btn_aceptar.clicked.connect(self.aceptar)
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Si estamos modificando, cargar datos existentes
        if not self.modo_nuevo and self.usuario:
            self.input_usuario.setText(self.usuario['nombre'])
            self.combo_rol.setCurrentText(self.usuario['rol'])
        
    def aceptar(self):
        # Verificar credenciales del administrador
        admin_password = self.input_admin_password.text()
        if not verificar_credenciales(self.usuario_actual, admin_password)[0]:
            QMessageBox.warning(self, "Error", "Contraseña de administrador incorrecta")
            return
            
        nuevo_nombre = self.input_usuario.text()
        password = self.input_password.text()
        rol = self.combo_rol.currentText()
        
        if self.modo_nuevo:
            if crear_usuario(nuevo_nombre, password, rol):
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo crear el usuario")
        else:
            if modificar_usuario(self.usuario['id'], nuevo_nombre, password, rol):
                QMessageBox.information(self, "Éxito", "Usuario modificado correctamente")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "No se pudo modificar el usuario") 
                
