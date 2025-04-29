from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QWidget, QFormLayout, QDoubleSpinBox, QVBoxLayout, QDialog ,QAbstractItemView, QPushButton, QHeaderView, QTableWidgetItem, QLineEdit, QTableWidget, QComboBox, QHBoxLayout, QLabel, QMessageBox, QInputDialog
from db_postgres import agregar_stock_manual_db, agregar_lote_producto, get_db_connection, obtener_lotes_producto, clear_productos_cache, get_cached_productos, obtener_info_lote, marcar_lote_como_vendido, agregar_producto, actualizar_producto, buscar_producto, eliminar_producto, existe_producto, verificar_credenciales
from signals import signals
from PyQt6.QtCore import Qt
from datetime import datetime

class ProductosTab(QWidget):
    def __init__(self, usuario_actual):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.setObjectName("productos")
        self.producto_actual_id = None

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
        self.table = QTableWidget(0, 8)
        self.table.setObjectName("productTable")
        self.table.setHorizontalHeaderLabels(["ID", "Código", "Nombre", "Cantidad", "Tipo de Venta","Costo", "Venta", "Margen"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)  # Ocultar la columna de ID
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
        
        self.btn_agregar_stock = QPushButton("Agregar Stock")
        self.btn_agregar_stock.setObjectName("addButton")
        self.btn_agregar_stock.clicked.connect(self.agregar_stock_manual)
        self.btn_agregar_stock.setVisible(False)  # Inicialmente oculto
        
        form_layout.addWidget(self.btn_agregar_stock)

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
            clear_productos_cache()
            get_cached_productos()
            signals.producto_actualizado.emit()
            QApplication.processEvents()
            QMessageBox.information(self, "Éxito", "Producto agregado correctamente")
            self.limpiar_entradas()
            self.cargar_productos()
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

        producto_id = self.producto_actual_id
        print(f"ID del producto actual: {producto_id}")

        # Actualizar el producto en la base de datos
        if actualizar_producto(codigo, nombre, costo, venta, margen, cantidad, venta_por_peso, self.usuario_actual, producto_id):
            clear_productos_cache()
            get_cached_productos()
            signals.producto_actualizado.emit()
            clear_productos_cache()
            get_cached_productos()
            signals.producto_actualizado.emit()
            QApplication.processEvents()
            QMessageBox.information(self, "Éxito", "Producto actualizado correctamente")
            self.limpiar_entradas()
            self.cargar_productos()  # Actualizar lista de productos
        else:
            QMessageBox.warning(self, "Error", "No se pudo actualizar el producto")
            
    def cargar_datos_producto(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.producto_actual_id = int(self.table.item(row, 0).text())
        codigo = self.table.item(row, 1).text()
        nombre = self.table.item(row, 2).text()
        cantidad = self.table.item(row, 3).text()
        costo = self.table.item(row, 5).text()
        venta = self.table.item(row, 6).text()
        margen = self.table.item(row, 7).text()

        self.codigo_barras.setText(codigo)
        self.nombre.setText(nombre)
        self.cantidad.setText(cantidad)
        self.precio_costo.setText(costo)
        self.precio_venta.setText(venta)
        self.margen_ganancia.setText(margen)

        # Determinar si se vende por peso o por unidad
        venta_por_peso = 1 if "." in cantidad else 0
        self.tipo_venta.setCurrentText("Por Peso" if venta_por_peso else "Por Unidad")
        if venta_por_peso:
            self.toggle_lotes_button()

    def toggle_lotes_button(self):
        """Shows or hides the 'Gestionar Lotes' button based on product type and selection."""
        if self.producto_actual_id is not None:
            self.btn_agregar_stock.setVisible(True)
            # Optionally make quantity read-only for batch products
            # self.cantidad.setReadOnly(True)
        else:
            self.btn_agregar_stock.setVisible(False)
            # self.cantidad.setReadOnly(False)

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
            self.table.setItem(row, 0, QTableWidgetItem(str(producto[0])))  # ID
            mapping = {
                1: 1,  # codigo_barras -> Código
                2: 2,  # nombre -> Nombre
                4: 3,  # disponible -> Cantidad
                3: 4,  # venta_por_peso -> Tipo de Venta
                5: 5,  # precio_costo -> Costo
                6: 6,  # precio_venta -> Venta
                7: 7   # margen_ganancia -> Margen
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
        """Filtra los productos según búsqueda en la barra de búsqueda."""
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
        self.tipo_venta.setCurrentIndex(0)  # Por defecto, "Por Unidad"
        self.btn_agregar_stock.setVisible(False)
        self.producto_actual_id = None  # Reiniciar el ID del producto actua
        
        # Reconectar las señales
        self.precio_costo.textChanged.connect(self.calcular_margen_o_precio_venta)
        self.precio_venta.textChanged.connect(self.calcular_margen_o_precio_venta)
        self.margen_ganancia.textChanged.connect(self.calcular_margen_o_precio_venta)


    def mostrar_lotes_producto(self):
        """Muestra los lotes disponibles del producto actual"""
        if not hasattr(self, 'producto_actual_id') or not self.producto_actual_id:
            QMessageBox.warning(self, "Advertencia", "Primero debe seleccionar un producto")
            return
        
        # Verificar si el producto se vende por peso
        if not self.es_producto_por_peso():
            QMessageBox.information(self, "Información", 
                                "La gestión de lotes solo está disponible para productos que se venden por peso")
            return
        
        # Obtener lotes del producto
        lotes = obtener_lotes_producto(self.producto_actual_id)
        
        # Crear diálogo para mostrar lotes
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Lotes del Producto: {self.nombre.text()}")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Información del producto
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Producto: {self.nombre.text()}"))
        info_layout.addWidget(QLabel(f"Código: {self.codigo_barras.text() or 'N/A'}"))
        info_layout.addWidget(QLabel(f"Stock Total: {self.cantidad.text()} kg"))
        layout.addLayout(info_layout)
        
        # Tabla de lotes
        self.tabla_lotes = QTableWidget()
        self.tabla_lotes.setColumnCount(5)
        self.tabla_lotes.setHorizontalHeaderLabels(["ID", "Peso (kg)", "Fecha Creación", "Código", "Disponible"])
        
        # Configurar tabla
        self.tabla_lotes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_lotes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_lotes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Llenar tabla con lotes
        self.actualizar_tabla_lotes(lotes)
        
        layout.addWidget(self.tabla_lotes)
        
        # Botones de acción
        buttons_layout = QHBoxLayout()
        
        btn_agregar = QPushButton("Agregar Nuevo Lote")
        btn_agregar.clicked.connect(lambda: self.mostrar_dialogo_nuevo_lote(dialog))
        buttons_layout.addWidget(btn_agregar)
        
        btn_eliminar = QPushButton("Eliminar Lote")
        btn_eliminar.clicked.connect(self.eliminar_lote_seleccionado)
        buttons_layout.addWidget(btn_eliminar)
        
        btn_detalles = QPushButton("Ver Detalles")
        btn_detalles.clicked.connect(self.ver_detalles_lote)
        buttons_layout.addWidget(btn_detalles)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        buttons_layout.addWidget(btn_cerrar)
        
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        
        # Ejecutar diálogo
        dialog.exec()

    def actualizar_tabla_lotes(self, lotes):
        """Actualiza la tabla de lotes con los datos proporcionados"""
        self.tabla_lotes.setRowCount(len(lotes))
        
        for i, lote in enumerate(lotes):
            self.tabla_lotes.setItem(i, 0, QTableWidgetItem(str(lote[0])))  # ID
            self.tabla_lotes.setItem(i, 1, QTableWidgetItem(f"{lote[1]:.3f}"))  # Peso
            
            # Formatear fecha
            fecha = lote[2]
            if isinstance(fecha, datetime):
                fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
            else:
                fecha_str = str(fecha)
            
            self.tabla_lotes.setItem(i, 2, QTableWidgetItem(fecha_str))  # Fecha
            self.tabla_lotes.setItem(i, 3, QTableWidgetItem(lote[3]))  # Código
            
            # Estado (disponible/vendido)
            disponible = "Sí" if lote[4] else "No"
            self.tabla_lotes.setItem(i, 4, QTableWidgetItem(disponible))
            
            # Colorear filas según disponibilidad
            if not lote[4]:  # Si no está disponible
                for j in range(5):
                    item = self.tabla_lotes.item(i, j)
                    item.setBackground(QColor(240, 240, 240))  # Gris claro

    def mostrar_dialogo_nuevo_lote(self, parent_dialog):
        """Muestra un diálogo para agregar un nuevo lote"""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("Agregar Nuevo Lote")
        dialog.setMinimumWidth(300)
        
        layout = QFormLayout()
        
        # Campo para el peso
        self.peso_lote_input = QDoubleSpinBox()
        self.peso_lote_input.setRange(0.001, 1000.0)
        self.peso_lote_input.setDecimals(3)
        self.peso_lote_input.setSuffix(" kg")
        self.peso_lote_input.setValue(1.0)
        layout.addRow("Peso:", self.peso_lote_input)
        
        # Campo para código único (opcional)
        self.codigo_lote_input = QLineEdit()
        self.codigo_lote_input.setPlaceholderText("Dejar vacío para generar automáticamente")
        layout.addRow("Código (opcional):", self.codigo_lote_input)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(lambda: self.guardar_nuevo_lote(dialog))
        buttons_layout.addWidget(btn_guardar)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(dialog.reject)
        buttons_layout.addWidget(btn_cancelar)
        
        layout.addRow("", buttons_layout)
        dialog.setLayout(layout)
        
        dialog.exec()

    def guardar_nuevo_lote(self, dialog):
        """Guarda un nuevo lote en la base de datos"""
        peso = self.peso_lote_input.value()
        codigo = self.codigo_lote_input.text().strip() or None
        
        if peso <= 0:
            QMessageBox.warning(dialog, "Error", "El peso debe ser mayor que cero")
            return
        
        # Guardar lote en la base de datos
        lote_id = agregar_lote_producto(self.producto_actual_id, peso, codigo)
        
        if lote_id:
            QMessageBox.information(dialog, "Éxito", f"Lote agregado correctamente con ID: {lote_id}")
            dialog.accept()
            
            # Actualizar la tabla de lotes
            lotes = obtener_lotes_producto(self.producto_actual_id)
            self.actualizar_tabla_lotes(lotes)
            
            # Actualizar el stock total mostrado en el formulario principal
            self.actualizar_stock_producto()
        else:
            QMessageBox.critical(dialog, "Error", "No se pudo agregar el lote")

    def eliminar_lote_seleccionado(self):
        """Elimina el lote seleccionado (marcándolo como no disponible)"""
        selected_rows = self.tabla_lotes.selectedItems()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Debe seleccionar un lote para eliminar")
            return
        
        row = selected_rows[0].row()
        lote_id = int(self.tabla_lotes.item(row, 0).text())
        
        # Confirmar eliminación
        respuesta = QMessageBox.question(
            self, "Confirmar Eliminación", 
            "¿Está seguro de que desea eliminar este lote?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta == QMessageBox.StandardButton.Yes:
            # Marcar como no disponible
            if marcar_lote_como_vendido(lote_id):
                QMessageBox.information(self, "Éxito", "Lote eliminado correctamente")
                
                # Actualizar la tabla
                lotes = obtener_lotes_producto(self.producto_actual_id)
                self.actualizar_tabla_lotes(lotes)
                
                # Actualizar el stock total
                self.actualizar_stock_producto()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el lote")

    def ver_detalles_lote(self):
        """Muestra los detalles del lote seleccionado"""
        selected_rows = self.tabla_lotes.selectedItems()
        
        if not selected_rows:
            QMessageBox.warning(self, "Advertencia", "Debe seleccionar un lote para ver sus detalles")
            return
        
        row = selected_rows[0].row()
        lote_id = int(self.tabla_lotes.item(row, 0).text())
        
        # Obtener información detallada del lote
        lote_info = obtener_info_lote(lote_id)
        
        if not lote_info:
            QMessageBox.critical(self, "Error", "No se pudo obtener la información del lote")
            return
        
        # Mostrar información en un diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalles del Lote #{lote_info[5]}")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Información del lote
        form_layout = QFormLayout()
        form_layout.addRow("ID:", QLabel(str(lote_info[0])))
        form_layout.addRow("Producto:", QLabel(lote_info[6]))
        form_layout.addRow("Código Producto:", QLabel(lote_info[7] or "N/A"))
        form_layout.addRow("Peso:", QLabel(f"{lote_info[2]:.3f} kg"))
        
        # Formatear fecha
        fecha = lote_info[3]
        if isinstance(fecha, datetime):
            fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
        else:
            fecha_str = str(fecha)
        
        form_layout.addRow("Fecha Creación:", QLabel(fecha_str))
        form_layout.addRow("Código Único:", QLabel(lote_info[5]))
        form_layout.addRow("Disponible:", QLabel("Sí" if lote_info[4] else "No"))
        
        layout.addLayout(form_layout)
        
        # Botón cerrar
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        layout.addWidget(btn_cerrar)
        
        dialog.setLayout(layout)
        dialog.exec()

    def es_producto_por_peso(self):
        """Verifica si el producto actual se vende por peso"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT venta_por_peso FROM productos WHERE id = %s", 
                    (self.producto_actual_id,)
                )
                resultado = cursor.fetchone()
                return resultado and resultado[0] == 1
        except Exception as e:
            print(f"Error al verificar si el producto es por peso: {str(e)}")
            return False

    def actualizar_stock_producto(self):
        """Actualiza el stock mostrado en el formulario principal"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT disponible FROM productos WHERE id = %s", 
                    (self.producto_actual_id,)
                )
                stock = cursor.fetchone()[0]
                
                # Actualizar el campo de stock en la interfaz
                if hasattr(self, 'cantidad'):
                    self.cantidad.setText(f"{stock:.3f}")
        except Exception as e:
            print(f"Error al actualizar stock: {str(e)}")

    def agregar_stock_manual(self):
        """Muestra diálogo para agregar stock manualmente con comentario"""
        if not self.producto_actual_id:
            QMessageBox.warning(self, "Error", "Seleccione un producto primero")
            return
            
        # Crear diálogo personalizado
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Stock")
        layout = QVBoxLayout(dialog)
        
        # Campo para cantidad
        cantidad_layout = QHBoxLayout()
        cantidad_label = QLabel("Cantidad a agregar:")
        self.cantidad_input = QDoubleSpinBox()
        self.cantidad_input.setMinimum(0.001)
        self.cantidad_input.setDecimals(3)
        self.cantidad_input.setValue(1.0)
        cantidad_layout.addWidget(cantidad_label)
        cantidad_layout.addWidget(self.cantidad_input)
        
        # Crear campo adicional para comentario
        self.comentario_input = QLineEdit(dialog)
        self.comentario_input.setPlaceholderText("Comentario (opcional)")
        
        # Botones
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(dialog.accept)
        botones.rejected.connect(dialog.reject)
        
        # Configurar layout
        layout.addLayout(cantidad_layout)
        layout.addWidget(self.comentario_input)
        layout.addWidget(botones)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cantidad = self.cantidad_input.value()
            comentario = self.comentario_input.text().strip() or None
            
            if agregar_stock_manual_db(
                producto_id=self.producto_actual_id,
                cantidad=cantidad,
                usuario=self.usuario_actual,
                comentario=comentario
            ):
                QMessageBox.information(self, "Éxito", "Stock actualizado correctamente")
                self.cargar_productos()
                signals.producto_actualizado.emit()
                self.limpiar_entradas()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar el stock")