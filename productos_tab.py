from PyQt6.QtWidgets import QWidget, QVBoxLayout, QDialog ,QAbstractItemView, QPushButton, QHeaderView, QTableWidgetItem, QLineEdit, QTableWidget, QComboBox, QHBoxLayout, QLabel, QMessageBox, QInputDialog
from db_postgres import agregar_producto, actualizar_producto, buscar_producto, eliminar_producto, existe_producto, verificar_credenciales
from signals import signals
from PyQt6.QtCore import Qt

class ProductosTab(QWidget):
    def __init__(self, usuario_actual):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.setObjectName("productos")

        # Layout principal
        layout = QVBoxLayout()

        # Barra de búsqueda
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar producto por nombre o código de barras")
        self.search_bar.textChanged.connect(self.buscar_productos)
        signals.venta_realizada.connect(self.cargar_productos)
        signals.actualizar_modificaciones.connect(self.cargar_productos)
        layout.addWidget(self.search_bar)

        # Tabla de productos
        self.table = QTableWidget(0, 7)
        self.table.setObjectName("productTable")
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Cantidad", "Tipo de Venta","Costo", "Venta", "Margen"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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
        self.cargar_productos()
        
    def cargar_productos(self):
        """Carga todos los productos desde la base de datos y los almacena en memoria."""
        self.productos = buscar_producto()  # Cargar todos los productos
        self.actualizar_tabla(self.productos)  # Mostrar todos los productos en la tabla
        
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

    def verificar_credenciales_usuario(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Verificación")
        dialog.setLabelText("Ingrese su contraseña:")
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            password = dialog.textValue()
            # Verificar las credenciales del usuario actual
            if verificar_credenciales(self.usuario_actual, password)[0]:
                return True
        return False

    def agregar_producto(self):
        if not self.verificar_credenciales_usuario():
            QMessageBox.warning(self, "Error", "Contraseña incorrecta")
            return

        # Solo validamos el nombre como campo requerido
        if not self.nombre.text():
            QMessageBox.warning(self, "Error", "Por favor, ingrese al menos el nombre del producto.")
            return
        
        codigo = self.codigo_barras.text() or None  # Si está vacío, será None
        nombre = self.nombre.text()
        venta_por_peso = 1 if self.tipo_venta.currentText() == "Por Peso" else 0

        # Verificar duplicados solo por nombre
        if existe_producto(None, nombre):  # Modificar la función existe_producto
            QMessageBox.warning(self, "Error", "Ya existe un producto con ese nombre.")
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

        if agregar_producto(codigo, nombre, costo, venta, margen, cantidad, venta_por_peso, self.usuario_actual):
            QMessageBox.information(self, "Éxito", "Producto agregado correctamente")
            self.limpiar_entradas()
            self.cargar_productos()
            signals.producto_actualizado.emit()
        else:
            QMessageBox.warning(self, "Error", "No se pudo agregar el producto")

    def actualizar_producto(self):
        if not self.verificar_credenciales_usuario():
            QMessageBox.warning(self, "Error", "Contraseña incorrecta")
            return

        # Validación de campos
        if not self.codigo_barras.text() and not self.nombre.text():
            QMessageBox.warning(self, "Error", "Por favor, complete al menos el código de barras o el nombre del producto.")
            return
            
        codigo = self.codigo_barras.text() or None
        nombre = self.nombre.text() or None
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
        if actualizar_producto(codigo, nombre, costo, venta, margen, cantidad, venta_por_peso, self.usuario_actual):
            QMessageBox.information(self, "Éxito", "Producto actualizado correctamente")
            self.limpiar_entradas()
            self.cargar_productos()  # Actualizar lista de productos
            signals.producto_actualizado.emit()
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
        if not self.verificar_credenciales_usuario():
            QMessageBox.warning(self, "Error", "Contraseña incorrecta")
            return

        nombre = self.nombre.text()
        if not nombre:
            QMessageBox.warning(self, "Error", "Seleccione un producto para eliminar")
            return

        # First try normal deletion
        success, message = eliminar_producto(nombre, self.usuario_actual, force_delete=False)
        
        if not success and "tiene ventas asociadas" in message:
            # Ask user if they want to force delete
            respuesta = QMessageBox.question(
                self,
                "Producto con ventas",
                "Este producto tiene ventas asociadas. ¿Desea marcarlo como eliminado de todos modos?\n"
                "Esto mantendrá el historial de ventas pero el producto no estará disponible para nuevas ventas.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if respuesta == QMessageBox.StandardButton.Yes:
                # Try force delete
                success, message = eliminar_producto(nombre, self.usuario_actual, force_delete=True)
        
        if success:
            QMessageBox.information(self, "Éxito", message)
            self.limpiar_entradas()
            self.cargar_productos()
            signals.producto_actualizado.emit()
        else:
            QMessageBox.warning(self, "Error", message)                
                        
    def actualizar_tabla(self, productos):
        # Limpiar la tabla y mostrar los productos
        self.table.setRowCount(0)
        for producto in productos:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Map database columns to table columns:
            # Table columns: ["Código", "Nombre", "Cantidad", "Tipo de Venta", "Costo", "Venta", "Margen"]
            # DB columns:    [id, codigo_barras, nombre, venta_por_peso, disponible, precio_costo, precio_venta, margen_ganancia]
            
            mapping = {
                1: 0,  # codigo_barras -> Código
                2: 1,  # nombre -> Nombre
                4: 2,  # disponible -> Cantidad
                3: 3,  # venta_por_peso -> Tipo de Venta
                5: 4,  # precio_costo -> Costo
                6: 5,  # precio_venta -> Venta
                7: 6   # margen_ganancia -> Margen
            }

            for db_index, table_index in mapping.items():
                dato = producto[db_index]

                # Convertir "venta_por_peso" a texto "Unidad" o "Peso"
                if db_index == 3:
                    dato = "Peso" if dato == 1 else "Unidad"

                # Formatear la columna "Cantidad"
                if db_index == 4:
                    cantidad = float(dato)
                    if producto[3] == 0:  # Si venta_por_peso es 0
                        dato = int(cantidad)
                    else:
                        dato = cantidad

                self.table.setItem(row, table_index, QTableWidgetItem(str(dato)))
                
    def buscar_productos(self):
        """Filtra los productos según la búsqueda en la barra de búsqueda."""
        term = self.search_bar.text().lower()  # Convertir a minúsculas para comparación
        productos_filtrados = [
            producto for producto in self.productos
            if term in producto[1].lower() or term in producto[2].lower()  # Comparar con nombre y código
        ]
        self.actualizar_tabla(productos_filtrados)  # Actualizar la tabla con los productos filtrados 
           
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
    