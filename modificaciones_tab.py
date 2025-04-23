from PyQt6.QtWidgets import QWidget, QVBoxLayout, QAbstractItemView, QHeaderView ,QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout
from db_postgres import obtener_modificaciones
from signals import signals 
from datetime import datetime
import pytz
from PyQt6.QtCore import QTimer

class ModificacionesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Crear tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "Usuario", "Fecha/Hora", "Tipo", "Producto",
            "Campo", "Valor Anterior", "Valor Nuevo"
        ])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Crear un layout horizontal para el botón
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # Esto empujará el botón hacia la derecha

        # Crear botón de actualización
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setObjectName("actualizarModificaciones")
        self.btn_actualizar.clicked.connect(self.actualizar_modificaciones)
        btn_layout.addWidget(self.btn_actualizar)  # Agregar el botón al layout

        # Agregar el layout del botón y la tabla al layout principal
        layout.addLayout(btn_layout)  # Agregar el layout del botón
        layout.addWidget(self.tabla)   # Agregar la tabla
        layout.addSpacing(10)

        self.setLayout(layout)
        
        self.cargar_modificaciones()
        signals.producto_actualizado.connect(self.cargar_modificaciones)
        
    def formatear_nombre_campo(self, campo):
        mapeo_campos = {
            'disponible': 'Cantidad',
            'codigo_barras': 'Código de barras',
            'nombre': 'Nombre',
            'venta_por_peso': 'Venta por peso',
            'precio_costo': 'Precio de costo',
            'precio_venta': 'Precio de venta',
            'margen_ganancia': 'Margen de ganancia'
        }
        return mapeo_campos.get(campo, campo)
        
    def cargar_modificaciones(self):
        modificaciones = obtener_modificaciones()
        self.tabla.setRowCount(len(modificaciones))
        
        argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')
        utc_tz = pytz.utc

        for i, mod in enumerate(modificaciones):
            # Usuario
            self.tabla.setItem(i, 0, QTableWidgetItem(mod['usuario']))
            
            # Fecha/Hora
            try:
                fecha_hora = mod['fecha_hora']
                if fecha_hora:
                    if isinstance(fecha_hora, str):
                        fecha_hora = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S%z")
                    if fecha_hora.tzinfo is None:
                        fecha_hora = pytz.utc.localize(fecha_hora)
                    fecha_local = fecha_hora.astimezone(argentina_tz)
                    fecha_formateada = fecha_local.strftime("%d/%m/%Y %H:%M")
                    self.tabla.setItem(i, 1, QTableWidgetItem(fecha_formateada))
                else:
                    self.tabla.setItem(i, 1, QTableWidgetItem(""))
            except Exception as e:
                print(f"Error al convertir fecha: {e}")
                self.tabla.setItem(i, 1, QTableWidgetItem(str(mod['fecha_hora'])))

            # Tipo
            self.tabla.setItem(i, 2, QTableWidgetItem(mod['tipo_modificacion']))
            
            # Producto
            self.tabla.setItem(i, 3, QTableWidgetItem(mod['producto_nombre']))
            
            # Campo (con formato)
            campo_formateado = self.formatear_nombre_campo(mod['campo_modificado']) if mod['campo_modificado'] else ''
            self.tabla.setItem(i, 4, QTableWidgetItem(campo_formateado))
            
            # Valor anterior
            self.tabla.setItem(i, 5, QTableWidgetItem(str(mod['valor_anterior'] or '')))
            
            # Valor nuevo
            self.tabla.setItem(i, 6, QTableWidgetItem(str(mod['valor_nuevo'] or '')))
            
        self.btn_actualizar.setEnabled(True)  # Deshabilitar el botón de actualización
        signals.actualizar_modificaciones.emit()


    def actualizar_modificaciones(self):
        # Vaciar la tabla
        self.tabla.setRowCount(0)  # Borra todas las filas de la tabla
        self.btn_actualizar.setEnabled(False)  # Deshabilitar el botón de actualización

        # Configurar un temporizador para esperar 1 segundo antes de cargar las modificaciones
        QTimer.singleShot(1000, self.cargar_modificaciones)  # Esperar 1000 milisegundos (1 segundo)