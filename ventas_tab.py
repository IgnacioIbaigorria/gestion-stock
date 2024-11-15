from PyQt6.QtWidgets import QWidget, QVBoxLayout, QDialog, QDialogButtonBox, QInputDialog, QPushButton, QHeaderView, QCompleter, QLineEdit, QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QMessageBox, QComboBox
from PyQt6.QtCore import Qt, QStringListModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from db import obtener_producto_por_codigo, obtener_producto_por_id,registrar_venta, buscar_coincidencias_producto
import os

class CustomInputDialog(QDialog):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingresar cantidad")

        # Crear layout principal
        layout = QVBoxLayout(self)

        # Crear la etiqueta
        self.label = QLabel(label_text, self)
        layout.addWidget(self.label)

        # Crear el campo de entrada
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Ingrese cantidad")
        self.input_field.setStyleSheet("""
            font-size: 20px;
            border: 2px solid #cccccc;
            border-radius: 8px;
            padding: 8px;
        """)
        self.input_field.setMinimumHeight(40)
        layout.addWidget(self.input_field)

        # Crear botones OK y Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        layout.addWidget(self.button_box)

        # Conectar señales
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_value(self):
        return self.input_field.text()

def parsear_codigo_producto(codigo_barras):
    # Verificar si el código de barras pertenece a un producto a peso variable
    if len(codigo_barras) == 13 and codigo_barras[:2] == "20":  # Prefijo '20' indica peso variable
        codigo_producto = codigo_barras[2:6]  # Código de producto (4 dígitos siguientes)
        peso_gramos = int(codigo_barras[6:11])  # Extraer el peso en gramos (5 dígitos)
        peso_kg = peso_gramos / 1000  # Convertir a kg
        return {
            "tipo": "peso_variable",
            "codigo_producto": codigo_producto,
            "peso_kg": peso_kg
        }
    
    # Si no es peso variable, lo tratamos como un producto unitario
    return {
        "tipo": "unitario",
        "codigo_producto": codigo_barras
    }

class VentasTab(QWidget):
    def __init__(self):
        super().__init__()

        # Layout principal
        layout = QVBoxLayout()

        # Entrada de código de barras o nombre del producto
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("Ingresar código de barras o nombre del producto")
        self.product_input.textChanged.connect(self.actualizar_autocompletado)
        self.product_input.returnPressed.connect(self.agregar_producto)
        
        # Configuración de autocompletado
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.product_input.setCompleter(self.completer)
        
        layout.addWidget(self.product_input)

        # Tabla de productos en la venta actual
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Cantidad", "Precio"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Selector de método de pago
        self.payment_method = QComboBox()
        self.payment_method.addItems(["Efectivo", "Débito", "Transferencia", "A Crédito"])
        layout.addWidget(QLabel("Método de Pago:"))
        layout.addWidget(self.payment_method)

        totales = QHBoxLayout()
        
        # Total de la venta
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setObjectName("total")
        totales.addWidget(self.total_label)
        
        # Entrada de monto pagado
        self.amount_paid = QLineEdit()
        self.amount_paid.setPlaceholderText("Monto pagado")
        self.amount_paid.textChanged.connect(self.calcular_vuelto)
        totales.addWidget(self.amount_paid)

        # Monto de vuelto
        self.change_label = QLabel("Vuelto: $0.00")
        self.total_label.setObjectName("vuelto")
        totales.addWidget(self.change_label)

        totales_widget = QWidget()
        totales_widget.setLayout(totales)
        layout.addWidget(totales_widget)

        # Botón para registrar la venta
        remove_sale_button = QPushButton("QUITAR")
        remove_sale_button.clicked.connect(self.quitar_producto_venta)
        remove_sale_button.setObjectName("quitarProducto")

        register_sale_button = QPushButton("REGISTRAR VENTA")
        register_sale_button.clicked.connect(self.registrar_venta)
        register_sale_button.setObjectName("registrarVenta")

        sale_button_layout = QHBoxLayout()
        sale_button_layout.addWidget(remove_sale_button)
        sale_button_layout.addWidget(register_sale_button)
        button_widget = QWidget()
        button_widget.setLayout(sale_button_layout)
        layout.addWidget(button_widget)


        self.setLayout(layout)

        # Variables para almacenar datos de venta
        self.lista_productos = []
        self.total = 0.0

        
    def actualizar_autocompletado(self):
        # Obtener el texto actual del input
        texto = self.product_input.text().strip()
        if len(texto) >= 1:  # Inicia búsqueda si hay al menos 1 caracter
            coincidencias = buscar_coincidencias_producto(texto)
            model = QStringListModel(coincidencias)  # Crear modelo de lista de strings
            self.completer.setModel(model)  # Asignar el modelo al QCompleter


    def agregar_producto(self):
        codigo_o_nombre = self.product_input.text().strip()
        producto = obtener_producto_por_codigo(codigo_o_nombre)
        
        if not producto:
            QMessageBox.warning(self, "Producto no encontrado", "No se encontró un producto con el código o nombre proporcionado.")
            return

        id, codigo, nombre, precio_costo, precio_venta, margen_ganancia, familia, venta_por_peso, disponible = producto[:9]

        # Comprobar si el producto ya está en la lista de productos agregados
        for i, (prod_id, cantidad_existente, precio_total_existente) in enumerate(self.lista_productos):
            if prod_id == id:
                # Producto ya existe, entonces vamos a sumar la cantidad
                if venta_por_peso == 1:
                    # Producto vendido por peso
                    dialog = CustomInputDialog(f"Ingrese el peso en kilogramos para {nombre}:")
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        try:
                            peso = float(dialog.get_value())
                            if peso <= 0:
                                raise ValueError("Peso inválido")
                            
                            # Verificar si hay suficiente stock
                            if (cantidad_existente + peso) > disponible:
                                raise ValueError("No hay suficiente cantidad del producto")

                            # Actualizar la cantidad y el precio total
                            nueva_cantidad = cantidad_existente + peso
                            nuevo_precio_total = nueva_cantidad * precio_venta
                            
                            # Actualizar en la tabla y en la lista de productos
                            self.lista_productos[i] = (id, nueva_cantidad, nuevo_precio_total)
                            self.table.item(i, 2).setText(str(nueva_cantidad))
                            self.table.item(i, 3).setText(f"${nuevo_precio_total:.2f}")

                            # Actualizar el total de la venta
                            self.total += peso * precio_venta
                            self.actualizar_total()
                        except ValueError as e:
                            QMessageBox.warning(self, "Valor inválido", str(e))
                        return
                else:
                    # Producto vendido por unidad
                    dialog = CustomInputDialog(f"Ingrese la cantidad de unidades para {nombre}:")
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        try:
                            cantidad = int(dialog.get_value())
                            if cantidad <= 0:
                                raise ValueError("Cantidad inválida")
                            
                            # Verificar si hay suficiente stock
                            if (cantidad_existente + cantidad) > disponible:
                                raise ValueError("No hay suficiente stock del producto")

                            # Actualizar la cantidad y el precio total
                            nueva_cantidad = cantidad_existente + cantidad
                            nuevo_precio_total = nueva_cantidad * precio_venta

                            # Actualizar en la tabla y en la lista de productos
                            self.lista_productos[i] = (id, nueva_cantidad, nuevo_precio_total)
                            self.table.item(i, 2).setText(str(nueva_cantidad))
                            self.table.item(i, 3).setText(f"${nuevo_precio_total:.2f}")

                            # Actualizar el total de la venta
                            self.total += cantidad * precio_venta
                            self.actualizar_total()
                        except ValueError as e:
                            QMessageBox.warning(self, "Valor inválido", str(e))
                        return

        # Si el producto no estaba en la lista, se añade normalmente
        if venta_por_peso == 1:
            # Producto vendido por peso
            dialog = CustomInputDialog(f"Ingrese el peso en kilogramos para {nombre}:")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    peso = float(dialog.get_value())
                    if peso <= 0:
                        raise ValueError("Peso inválido")
                    
                    if peso > disponible:
                        raise ValueError("No hay suficiente cantidad del producto")
                    
                    precio_total = peso * precio_venta
                    cantidad = peso  # Guardar el peso como cantidad
                except ValueError as e:
                    QMessageBox.warning(self, "Valor inválido", str(e))
                    return
        else:
            # Producto vendido por unidad
            dialog = CustomInputDialog(f"Ingrese la cantidad de unidades para {nombre}:")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    cantidad = int(dialog.get_value())
                    if cantidad <= 0:
                        raise ValueError("Cantidad inválida")
                    
                    if cantidad > disponible:
                        raise ValueError("No hay suficiente stock del producto")
                    
                    precio_total = cantidad * precio_venta
                except ValueError as e:
                    QMessageBox.warning(self, "Valor inválido", str(e))
                    return

        # Añadir el nuevo producto a la tabla
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(codigo))
        self.table.setItem(row, 1, QTableWidgetItem(nombre))
        self.table.setItem(row, 2, QTableWidgetItem(str(cantidad)))
        self.table.setItem(row, 3, QTableWidgetItem(f"${precio_total:.2f}"))

        # Agregar el producto al carrito
        self.lista_productos.append((id, cantidad, precio_total))
        self.total += precio_total
        self.actualizar_total()
        self.product_input.clear()


    def quitar_producto_venta(self):
        # Obtener el índice del producto seleccionado
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Seleccione un producto", "Seleccione un producto para quitar.")
            return

        # Quitar el producto de la lista y de la tabla
        producto_eliminado = self.lista_productos.pop(row)
        self.total -= producto_eliminado[2]  # Resta el precio del producto eliminado al total
        self.table.removeRow(row)
        self.actualizar_total()

    
    def actualizar_total(self):
        self.total_label.setText(f"Total: ${self.total:.2f}")

    def calcular_vuelto(self):
        try:
            monto_pagado = float(self.amount_paid.text())
            if self.payment_method.currentText() == "Efectivo":
                vuelto = monto_pagado - self.total
                self.change_label.setText(f"Vuelto: ${vuelto:.2f}")
            else:
                self.change_label.setText("Vuelto: $0.00")
                vuelto = 0
        except ValueError:
            self.change_label.setText("Vuelto: $0.00")

    def registrar_venta(self):
        # Verificar si se han añadido productos
        if not self.lista_productos:
            QMessageBox.warning(self, "Venta vacía", "No se han agregado productos a la venta.")
            return

        # Confirmar registro de la venta
        metodo_pago = self.payment_method.currentText()
        
        try:
            monto_pagado = float(self.amount_paid.text())  # Convertir el texto ingresado a un número
        except ValueError:
            QMessageBox.warning(self, "Error", "Por favor, ingrese un valor numérico válido en el campo de pago.")
            return

        if monto_pagado < self.total:
            QMessageBox.warning(self, "Cargar pago", "El pago no puede ser menor al total de la venta.")
            return
        
        if metodo_pago == "Efectivo":
            vuelto = monto_pagado - self.total
        else:
            vuelto = 0
        exito, venta_id = registrar_venta(self.lista_productos, self.total, metodo_pago)
        
        if exito:
            # Generar el ticket
            self.generar_ticket(venta_id, self.lista_productos, self.total, metodo_pago, vuelto, monto_pagado)
            
            QMessageBox.information(self, "Venta registrada", "La venta se ha registrado correctamente.")
            self.lista_productos.clear()
            self.table.setRowCount(0)
            self.total = 0.0
            self.actualizar_total()
            self.amount_paid.clear()
            self.change_label.setText("Vuelto: $0.00")
        else:
            QMessageBox.warning(self, "Error", "No se pudo registrar la venta.")

    def generar_ticket(self, venta_id, lista_productos, total, metodo_pago, vuelto, monto_pagado):
        # Directorio para almacenar los tickets
        directorio_tickets = "tickets/"
        if not os.path.exists(directorio_tickets):
            os.makedirs(directorio_tickets)

        # Nombre y ruta del archivo PDF
        nombre_archivo = f"ticket_{venta_id}.pdf"
        ruta_ticket = os.path.join(directorio_tickets, nombre_archivo)

        # Crear el canvas de ReportLab
        pdf = canvas.Canvas(ruta_ticket, pagesize=A4)
        pdf.setTitle("Ticket de Venta")

        # Configuración inicial del ticket
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, 800, "Carnicería XYZ")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(100, 780, "="*40)
        pdf.drawString(100, 760, f"ID de venta: {venta_id}")
        pdf.drawString(100, 740, "="*40)
        pdf.drawString(100, 720, "Productos:")

        # Posición inicial para listar productos
        y_position = 700

        # Recorrer productos y generar cada línea del ticket
        for producto_id, cantidad, precio_total in lista_productos:
            producto = obtener_producto_por_id(producto_id)
            
            # Verifica si el producto existe en la base de datos
            if producto is None:
                QMessageBox.warning(self, "Error", f"Producto con ID {producto_id} no encontrado.")
                continue  # Saltar al siguiente producto si no se encuentra

            # Extraer nombre y precio unitario del producto
            nombre = producto[2]  # Nombre del producto
            precio_unitario = producto[4]  # Precio unitario o por kg

            # Determinar si el producto es a peso variable o unitario
            if isinstance(cantidad, float):  # Producto a peso variable
                texto_producto = f"{nombre} - {cantidad:.2f}kg x ${precio_unitario:.2f}/kg = ${precio_total:.2f}"
            else:
                texto_producto = f"{nombre} - Cantidad: {cantidad} - Precio Total: ${precio_total:.2f}"

            # Dibujar el texto del producto
            pdf.drawString(100, y_position, texto_producto)
            y_position -= 20  # Desplazar hacia abajo para el siguiente producto

            # Si llegamos al final de la página, crear una nueva
            if y_position < 100:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y_position = 800

        # Continuar con los detalles finales de la venta
        pdf.drawString(100, y_position - 20, "="*40)
        pdf.drawString(100, y_position - 40, f"Método de pago: {metodo_pago}")
        pdf.drawString(100, y_position - 60, f"Total: ${total:.2f}")
        if metodo_pago == "Efectivo":
            pdf.drawString(100, y_position - 80, f"Su pago: ${monto_pagado:.2f}")
            pdf.drawString(100, y_position - 100, f"Vuelto: ${vuelto:.2f}")
        pdf.drawString(100, y_position - 120, "Gracias por su compra")
        pdf.drawString(100, y_position - 140, "="*40)

        # Guardar el archivo PDF
        pdf.save()

        # Mensaje de confirmación
        QMessageBox.information(self, "Ticket Generado", f"El ticket de venta ha sido guardado en {ruta_ticket}")
