from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHeaderView, QTableWidgetItem, QLineEdit, QTableWidget, QComboBox, QHBoxLayout, QLabel, QMessageBox
from db import agregar_producto, actualizar_producto, buscar_producto, eliminar_producto, existe_producto
from signals import signals
from PyQt6.QtCore import Qt

class ProductosTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setObjectName("productos")

        # Layout principal
        layout = QVBoxLayout()

        # Barra de búsqueda
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar producto por nombre o código de barras")
        self.search_bar.textChanged.connect(self.buscar_productos)
        signals.venta_realizada.connect(self.buscar_productos)
        layout.addWidget(self.search_bar)

        # Tabla de productos
        self.table = QTableWidget(0, 7)
        self.table.setObjectName("productTable")
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Cantidad", "Tipo de Venta","Costo", "Venta", "Margen"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.cargar_datos_producto)  # Conectar selección a método
        layout.addWidget(self.table)

        # Formulario para agregar/editar productos
        form_layout = QHBoxLayout()
        self.codigo_barras = QLineEdit()
        self.codigo_barras.setPlaceholderText("Código de Barras")
        form_layout.addWidget(self.codigo_barras)
        
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre")
        form_layout.addWidget(self.nombre)
        
        self.cantidad = QLineEdit()
        self.cantidad.setPlaceholderText("Cantidad")
        form_layout.addWidget(self.cantidad)
        
        self.tipo_venta = QComboBox()
        self.tipo_venta.addItems(["Por Unidad", "Por Peso"])
        form_layout.addWidget(self.tipo_venta)
        
        self.precio_costo = QLineEdit()
        self.precio_costo.setPlaceholderText("Precio de costo")
        self.precio_costo.textChanged.connect(self.calcular_margen_o_precio_venta)
        form_layout.addWidget(self.precio_costo)
        
        self.precio_venta = QLineEdit()
        self.precio_venta.setPlaceholderText("Precio de venta")
        self.precio_venta.textChanged.connect(self.calcular_margen_o_precio_venta)
        form_layout.addWidget(self.precio_venta)
        
        self.margen_ganancia = QLineEdit()
        self.margen_ganancia.setPlaceholderText("Margen de ganancia")
        self.margen_ganancia.textChanged.connect(self.calcular_margen_o_precio_venta)
        form_layout.addWidget(self.margen_ganancia)
        
        layout.addLayout(form_layout)

        # Botones
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Agregar Producto")
        self.add_button.setObjectName("addButton")
        self.add_button.clicked.connect(self.agregar_producto)
        button_layout.addWidget(self.add_button)
        
        self.update_button = QPushButton("Actualizar Producto")
        self.update_button.setObjectName("updateButton")
        self.update_button.clicked.connect(self.actualizar_producto)
        button_layout.addWidget(self.update_button)
        
        self.delete_button = QPushButton("Eliminar Producto")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.eliminar_producto)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

        # Cargar todos los productos al iniciar
        self.buscar_productos()
        
    def calcular_margen_o_precio_venta(self):
        """
        Este método se ejecuta automáticamente cada vez que el usuario cambia un valor
        en los campos de texto relacionados con el costo, precio de venta o margen de ganancia.
        """

        try:
            costo = float(self.precio_costo.text()) if self.precio_costo.text() else None
            venta = float(self.precio_venta.text()) if self.precio_venta.text() else None
            margen = float(self.margen_ganancia.text()) if self.margen_ganancia.text() else None
        except ValueError:
            # Si el texto no es válido (no es número), no hacer nada
            return

        # Si se cambió el precio de costo y el precio de venta, calculamos el margen
        if costo is not None and venta is not None:
            margen_calculado = ((venta - costo) / costo) * 100
            self.margen_ganancia.setText(f"{margen_calculado:.2f}")
        
        # Si se cambió el precio de costo y el margen, calculamos el precio de venta
        elif costo is not None and margen is not None:
            precio_venta_calculado = costo * (1 + (margen / 100))
            self.precio_venta.setText(f"{precio_venta_calculado:.2f}")

        # Si se cambió el precio de venta y el margen, recalculamos el precio de costo
        elif venta is not None and margen is not None:
            precio_costo_calculado = venta / (1 + (margen / 100))
            self.precio_costo.setText(f"{precio_costo_calculado:.2f}")

    def agregar_producto(self):
        if not self.codigo_barras.text() or not self.nombre.text():
            QMessageBox.warning(self, "Error", "Por favor, complete todos los campos requeridos.")
            return
        
        codigo = self.codigo_barras.text()
        nombre = self.nombre.text()
        venta_por_peso = 1 if self.tipo_venta.currentText() == "Por Peso" else 0

        # Verificar duplicados
        if existe_producto(codigo, nombre):
            QMessageBox.warning(self, "Error", "Ya existe un producto con ese código de barras o nombre.")
            return

        try:
            cantidad = float(self.cantidad.text())
            if not venta_por_peso:
                cantidad = int(cantidad)  # Por unidad debe ser un entero
            costo = float(self.precio_costo.text())
            venta = float(self.precio_venta.text())
            margen = float(self.margen_ganancia.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Los campos de cantidad, costo, venta y margen deben ser números.")
            return

        if agregar_producto(codigo, nombre, costo, venta, margen, cantidad, venta_por_peso):
            QMessageBox.information(self, "Éxito", "Producto agregado correctamente")
            self.limpiar_entradas()
            self.buscar_productos()
        else:
            QMessageBox.warning(self, "Error", "No se pudo agregar el producto")

    def actualizar_producto(self):
        # Validación de campos
        if not self.codigo_barras.text() or not self.nombre.text():
            QMessageBox.warning(self, "Error", "Por favor, complete todos los campos requeridos.")
            return
                
        codigo = self.codigo_barras.text()
        nombre = self.nombre.text()
        venta_por_peso = 1 if self.tipo_venta.currentText() == "Por Peso" else 0

        # Intentar convertir los valores de costo, venta y margen
        try:
            cantidad = float(self.cantidad.text())
            if not venta_por_peso:
                cantidad = int(cantidad)  # Por unidad debe ser un entero
            costo = float(self.precio_costo.text())
            venta = float(self.precio_venta.text())
            margen = float(self.margen_ganancia.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Los campos de cantidad, costo, venta y margen deben ser números.")
            return

        # Actualizar el producto en la base de datos
        if actualizar_producto(codigo, nombre, costo, venta, margen, cantidad, venta_por_peso):
            QMessageBox.information(self, "Éxito", "Producto actualizado correctamente")
            self.limpiar_entradas()
            self.buscar_productos()  # Actualizar lista de productos
        else:
            QMessageBox.warning(self, "Error", "No se pudo actualizar el producto")
            
    def cargar_datos_producto(self):
        row = self.table.currentRow()
        if row < 0:
            return

        codigo = self.table.item(row, 0).text()
        nombre = self.table.item(row, 1).text()
        cantidad = self.table.item(row, 2).text()
        costo = self.table.item(row, 4).text()
        venta = self.table.item(row, 5).text()
        margen = self.table.item(row, 6).text()

        self.codigo_barras.setText(codigo)
        self.nombre.setText(nombre)
        self.cantidad.setText(cantidad)
        self.precio_costo.setText(costo)
        self.precio_venta.setText(venta)
        self.margen_ganancia.setText(margen)

        # Determinar si se vende por peso o por unidad
        venta_por_peso = 1 if "." in cantidad else 0
        self.tipo_venta.setCurrentText("Por Peso" if venta_por_peso else "Por Unidad")


    def eliminar_producto(self):
        # Crear el cuadro de diálogo de pregunta
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("Eliminar producto")
        mensaje.setText("¿Está seguro de eliminar el producto?")
        mensaje.setIcon(QMessageBox.Icon.Question)
        
        # Personalizar los botones
        btn_si = mensaje.addButton("Sí", QMessageBox.ButtonRole.YesRole)  # Correcto para PyQt6
        btn_no = mensaje.addButton("No", QMessageBox.ButtonRole.NoRole)  # Correcto para PyQt6
        
        # Establecer el botón por defecto
        mensaje.setDefaultButton(btn_no)
        
        # Mostrar el cuadro de diálogo
        mensaje.exec()

        # Verificar cuál botón fue presionado
        if mensaje.clickedButton() == btn_si:
            nombre = self.nombre.text()
            if eliminar_producto(nombre):
                QMessageBox.information(self, "Éxito", "Producto eliminado correctamente")
                self.limpiar_entradas()
                self.buscar_productos()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar el producto")
        else:
            return
            
    def actualizar_tabla(self, productos):
        # Limpiar la tabla y mostrar los productos
        self.table.setRowCount(0)
        for producto in productos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            for i, dato in enumerate(producto):
                # Convertir "venta_por_peso" a texto "Unidad" o "Peso"
                if i == 3:  # Suponiendo que la columna venta_por_peso está en la posición 3
                    es_por_peso = dato == 1  # True si es por peso
                    dato = "Unidad" if not es_por_peso else "Peso"

                # Formatear la columna "Cantidad" (posición 2) como entero si es por unidad
                if i == 2:  # Suponiendo que la columna cantidad está en la posición 2
                    cantidad = float(producto[2])  # Asegúrate de que el valor sea float
                    if not producto[3]:  # Si venta_por_peso es 0
                        dato = int(cantidad)  # Convertir a entero
                    else:
                        dato = cantidad  # Mantenerlo como float

                # Añadir el dato procesado a la celda correspondiente
                self.table.setItem(row, i, QTableWidgetItem(str(dato)))

    def buscar_productos(self):
        # Filtrado de productos según la búsqueda
        term = self.search_bar.text()
        productos = buscar_producto(term)
        self.actualizar_tabla(productos)
    
    def limpiar_entradas(self):
        # Desconectar señales para evitar cálculos automáticos al limpiar
        self.precio_costo.textChanged.disconnect()
        self.precio_venta.textChanged.disconnect()
        self.margen_ganancia.textChanged.disconnect()

        # Limpiar los campos de texto
        self.search_bar.clear()
        self.nombre.clear()
        self.cantidad.clear()
        self.codigo_barras.clear()
        self.precio_costo.clear()
        self.precio_venta.clear()
        self.margen_ganancia.clear()
        
        # Reconectar las señales
        self.precio_costo.textChanged.connect(self.calcular_margen_o_precio_venta)
        self.precio_venta.textChanged.connect(self.calcular_margen_o_precio_venta)
        self.margen_ganancia.textChanged.connect(self.calcular_margen_o_precio_venta)

                