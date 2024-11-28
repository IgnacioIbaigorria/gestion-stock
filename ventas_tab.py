from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QDialog, QDialogButtonBox, QInputDialog, QPushButton, QHeaderView, QCompleter, QLineEdit, QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QMessageBox, QComboBox
from PyQt6.QtCore import Qt, QStringListModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import simpleSplit
from db import fetch_productos, obtener_clientes, obtener_producto_por_codigo, obtener_producto_por_id,registrar_venta, buscar_coincidencias_producto
import os
from signals import signals

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
        
        # Configuración de autocompletado
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.product_input.setCompleter(self.completer)
        self.product_input.returnPressed.connect(self.agregar_producto)

        layout.addWidget(self.product_input)

        # Tabla de productos en la venta actual
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Cantidad", "Precio"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.actualizar_cantidad_producto)
        layout.addWidget(self.table)

        # Selector de método de pago
        self.payment_method = QComboBox()
        self.payment_method.addItems(["Efectivo", "Débito", "Transferencia", "A Crédito"])
        self.payment_method.currentIndexChanged.connect(self.mostrar_selector_cliente)
        layout.addWidget(QLabel("Método de Pago:"))
        layout.addWidget(self.payment_method)
        
        # Selector de cliente
        self.client_selector = QComboBox()
        self.client_selector.setPlaceholderText("-- Seleccionar Cliente --")
        self.cargar_clientes()  # Método para cargar clientes desde la base de datos
        self.client_selector.hide()  # Ocultar inicialmente
        layout.addWidget(self.client_selector)
        
        signals.cliente_agregado.connect(self.cargar_clientes)



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
        self.inicializar_completers()
        
    def inicializar_completers(self):
        """Inicializa los autocompletadores con datos actuales de productos."""
        nombres_productos = fetch_productos()
        self.completer.setModel(QStringListModel(nombres_productos))


    def mostrar_selector_cliente(self):
        """Muestra u oculta el selector de cliente según el método de pago."""
        if self.payment_method.currentText() == "A Crédito":
            self.client_selector.show()
        else:
            self.client_selector.hide()
    
    def cargar_clientes(self):
        """Carga la lista de clientes en el selector."""
        self.client_selector.clear()
        clientes = obtener_clientes()  # Función del back-end para obtener clientes
        self.client_selector.addItem("-- Seleccione un cliente --")
        for cliente in clientes:
            self.client_selector.addItem(cliente["nombre"], cliente["id"])

    
    def agregar_producto(self):
        codigo_o_nombre = self.product_input.text().strip()
        producto = obtener_producto_por_codigo(codigo_o_nombre)
        
        if not producto:
            QMessageBox.warning(self, "Producto no encontrado", "No se encontró un producto con el código o nombre proporcionado.")
            return

        id, codigo, nombre, precio_costo, precio_venta, margen_ganancia, venta_por_peso, disponible = producto[:8]

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
                    elif dialog.exec() == QDialog.DialogCode.Rejected:
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
                    else:
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
            else:
                return

        # Añadir el nuevo producto a la tabla
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(codigo))
        self.table.setItem(row, 1, QTableWidgetItem(nombre))
        self.table.setItem(row, 2, QTableWidgetItem(str(cantidad)))  # Editable
        self.table.setItem(row, 3, QTableWidgetItem(f"${precio_total:.2f}"))
        
        self.table.item(row, 2).setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)

        # Agregar el producto al carrito
        self.lista_productos.append((id, cantidad, precio_total))
        self.total += precio_total
        self.actualizar_total()
        self.product_input.clear()

    def actualizar_cantidad_producto(self, item: QTableWidgetItem):
        # Verifica si el cambio ocurre en la columna "Cantidad" (columna 2)
        if item.column() == 2:
            try:
                # Obtener el índice de la fila modificada
                row = item.row()

                # Validar si la fila corresponde a un índice válido en lista_productos
                if row >= len(self.lista_productos) or self.lista_productos[row] is None:
                    return

                # Obtener detalles del producto desde la lista
                producto_id, cantidad_anterior, precio_total_anterior = self.lista_productos[row]
                producto = obtener_producto_por_id(producto_id)  # Recuperar detalles del producto
                venta_por_peso = producto[7]  # Índice de venta_por_peso
                stock_disponible = producto[8]  # Índice de stock disponible

                # Obtener la nueva cantidad ingresada y validar el tipo de dato
                nueva_cantidad = item.text().strip()
                if venta_por_peso == 1:
                    # Producto vendido por peso, debe ser un número real
                    nueva_cantidad = float(nueva_cantidad)
                else:
                    # Producto vendido por unidad, debe ser un número entero
                    nueva_cantidad = int(nueva_cantidad)

                if nueva_cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a 0.")

                # Verificar stock disponible
                if nueva_cantidad > stock_disponible:
                    raise ValueError("No hay suficiente stock disponible.")

                # Calcular precio unitario y nuevo precio total
                precio_unitario = precio_total_anterior / cantidad_anterior
                nuevo_precio_total = nueva_cantidad * precio_unitario

                # Bloquear señales para evitar loops recursivos
                self.table.blockSignals(True)

                # Actualizar la lista de productos
                self.lista_productos[row] = (producto_id, nueva_cantidad, nuevo_precio_total)

                # Actualizar la tabla
                self.table.item(row, 3).setText(f"${nuevo_precio_total:.2f}")  # Columna 3: Precio total

                # Actualizar el total general
                self.total = sum(p[2] for p in self.lista_productos)
                self.actualizar_total()

                # Desbloquear señales
                self.table.blockSignals(False)

            except ValueError as e:
                QMessageBox.warning(self, "Cantidad inválida", str(e))

                # Restaurar el valor anterior en caso de error
                self.table.blockSignals(True)
                cantidad_anterior = self.lista_productos[row][1]
                item.setText(str(cantidad_anterior))
                self.table.blockSignals(False)

            except IndexError as e:
                QMessageBox.warning(self, "Error", str(e))


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

    def limpiar_datos_venta(self):
        """Limpia los datos de la venta para comenzar una nueva."""
        self.lista_productos.clear()
        self.table.setRowCount(0)
        self.total = 0.0
        self.actualizar_total()
        self.product_input.clear()
        self.amount_paid.clear()
        self.change_label.setText("Vuelto: $0.00")
        self.inicializar_completers()

    def registrar_venta(self):
        # Verificar si se han añadido productos
        if not self.lista_productos:
            QMessageBox.warning(self, "Venta vacía", "No se han agregado productos a la venta.")
            return

        # Confirmar registro de la venta
        metodo_pago = self.payment_method.currentText()

        if metodo_pago == "A Crédito":
            # Validar que se haya seleccionado un cliente
            cliente_id = self.client_selector.currentData()
            if cliente_id is None:
                QMessageBox.warning(self, "Error", "Debe seleccionar un cliente para registrar la venta a crédito.")
                return

            # Registrar la venta sin tomar pago
            exito, venta_id = registrar_venta(self.lista_productos, self.total, metodo_pago, cliente_id)

            if exito:
                QMessageBox.information(self, "Venta registrada", "La venta a crédito se ha registrado correctamente.")
                
                # Limpiar los datos de la venta
                self.limpiar_datos_venta()
            else:
                QMessageBox.warning(self, "Error", "No se pudo registrar la venta a crédito.")
        else:
            # Para otras formas de pago
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

            # Registrar la venta con el método de pago
            exito, venta_id = registrar_venta(self.lista_productos, self.total, metodo_pago)

            if exito:
                mensaje = QMessageBox(self)
                mensaje.setWindowTitle("Imprimir ticket")
                mensaje.setText("Desea imprimir el ticket?")
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
                    # Generar el ticket
                    self.generar_ticket(venta_id, self.lista_productos, self.total, metodo_pago, vuelto, monto_pagado)
                            
                QMessageBox.information(self, "Venta registrada", "La venta se ha registrado correctamente.")
                self.limpiar_datos_venta()
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
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Márgenes y ancho útil
        MARGEN_HORIZONTAL = 10
        ANCHO_TICKET = 58 * mm
        ANCHO_UTIL = ANCHO_TICKET - (2 * MARGEN_HORIZONTAL)

        # Calcular el número de líneas necesario
        lineas = 10  # Encabezado, separadores y detalles finales
        for producto_id, cantidad, precio_total in lista_productos:
            producto = obtener_producto_por_id(producto_id)
            if producto is None:
                continue

            # Preparar texto del producto
            nombre = producto[2]  # Nombre del producto
            precio_unitario = producto[4]  # Precio unitario o por kg
            if isinstance(cantidad, float):  # Producto a peso variable
                texto_producto = f"{nombre} - {cantidad:.2f}kg x ${precio_unitario:.2f}/kg = ${precio_total:.2f}"
            else:
                texto_producto = f"{nombre} - {cantidad} x ${precio_unitario:.2f} = ${precio_total:.2f}"

            # Dividir el texto en líneas según el ancho disponible
            lineas_producto = simpleSplit(texto_producto, "Helvetica", 8, ANCHO_UTIL)
            lineas += len(lineas_producto)  # Agregar las líneas requeridas por el producto

        if metodo_pago == "Efectivo":
            lineas += 2  # Líneas extra para "Vuelto" y "Pago"

        # Tamaño de cada línea (10 puntos) y margen adicional
        ALTURA_TICKET = (lineas * 10) + 30

        # Crear el canvas con altura dinámica
        pdf = canvas.Canvas(ruta_ticket, pagesize=(ANCHO_TICKET, ALTURA_TICKET))

        # Configuración inicial del ticket
        y_position = ALTURA_TICKET - 20  # Margen superior
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "Kiosco 25")
        y_position -= 10

        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "=" * 30)
        y_position -= 10
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, f"Fecha: {fecha_actual}")
        y_position -= 10
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "=" * 30)
        y_position -= 15

        # Listado de productos
        pdf.drawString(MARGEN_HORIZONTAL, y_position, "Productos:")
        y_position -= 10

        for producto_id, cantidad, precio_total in lista_productos:
            producto = obtener_producto_por_id(producto_id)
            if producto is None:
                QMessageBox.warning(self, "Error", f"Producto con ID {producto_id} no encontrado.")
                continue

            nombre = producto[2]  # Nombre del producto
            precio_unitario = producto[4]  # Precio unitario o por kg
            if isinstance(cantidad, float):  # Producto a peso variable
                texto_producto = f"{nombre} - {cantidad:.2f}kg x ${precio_unitario:.2f}/kg = ${precio_total:.2f}"
            else:
                texto_producto = f"{nombre} - {cantidad} x ${precio_unitario:.2f} = ${precio_total:.2f}"

            # Dividir el texto en líneas según el ancho disponible
            lineas_producto = simpleSplit(texto_producto, "Helvetica", 8, ANCHO_UTIL)
            for linea in lineas_producto:
                pdf.drawString(MARGEN_HORIZONTAL, y_position, linea)
                y_position -= 10

        # Detalles finales de la venta
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "=" * 30)
        y_position -= 10
        pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Método de pago: {metodo_pago}")
        y_position -= 10
        pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Total: ${total:.2f}")
        y_position -= 10

        if metodo_pago == "Efectivo":
            pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Su pago: ${monto_pagado:.2f}")
            y_position -= 10
            pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Vuelto: ${vuelto:.2f}")
            y_position -= 10

        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "Gracias por su compra")
        y_position -= 10
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "*NO VÁLIDO COMO FACTURA*")

        # Guardar el archivo PDF
        pdf.save()

        # Mensaje de confirmación
        QMessageBox.information(self, "Ticket Generado", f"El ticket de venta ha sido guardado en {ruta_ticket}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            term = self.product_input.text().strip()
            if term:
                self.agregar_producto()
