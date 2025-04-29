from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QDialog, QDialogButtonBox, QInputDialog, QPushButton, QHeaderView, QCompleter, QLineEdit, QTableWidget, QTableWidgetItem, QHBoxLayout, QLabel, QMessageBox, QComboBox
from PyQt6.QtCore import Qt, QStringListModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import simpleSplit
from config import get_db_path
from db_postgres import fetch_productos, obtener_lote_por_codigo_barras, obtener_info_lote, obtener_clientes, obtener_producto_por_codigo, obtener_producto_por_id,registrar_venta, buscar_coincidencias_producto
import os
from signals import signals
import logging
import win32print
import win32api

# Configuración del logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
    """
    Parsea un código de barras para determinar si es un producto de peso variable.
    
    Formato para productos de peso variable:
    "2" + "0" + [código del producto (5 dígitos)] + [peso en gramos (5 dígitos)] + dígito de control
    """
    print(f"Parseando código: {codigo_barras}")
    
    # Verificar si el código de barras pertenece a un producto a peso variable
    if len(codigo_barras) == 13 and codigo_barras.startswith("2"):  # Prefijo '2' indica peso variable
        # Formato: "2" + "0" + [código del producto (5 dígitos)] + [peso en gramos (5 dígitos)] + dígito de control
        codigo_producto = codigo_barras[2:7]  # Código de producto (5 dígitos)
        peso_gramos = int(codigo_barras[7:12])  # Extraer el peso en gramos (5 dígitos)
        peso_kg = peso_gramos / 1000  # Convertir a kg
        
        print(f"Producto de peso variable detectado: Código={codigo_producto}, Peso={peso_kg}kg")
        
        return {
            "tipo": "peso_variable",
            "codigo_producto": codigo_producto,
            "peso_kg": peso_kg
        }
    
    # Si no es peso variable, lo tratamos como un producto unitario
    print(f"Producto unitario detectado: Código={codigo_barras}")
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
        self.product_input.returnPressed.connect(self.on_return_pressed)

        layout.addWidget(self.product_input)

        # Tabla de productos en la venta actual
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "Cantidad", "Precio"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.actualizar_cantidad_producto)
        layout.addWidget(self.table)

        # Selector de método de pago
        self.payment_method = QComboBox()
        self.payment_method.addItems(["Efectivo", "Débito", "Transferencia", "Crédito"])
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
        signals.producto_actualizado.connect(self.inicializar_completers)



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
        nombres_productos = fetch_productos()
        print(f"Nombres de productos: {nombres_productos}")
        model = self.completer.model()
        if not model or not isinstance(model, QStringListModel):
            model = QStringListModel()
            self.completer.setModel(model)
        
        # Update existing model
        model.setStringList(nombres_productos)

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

    
    def on_return_pressed(self):
        codigo_o_nombre = self.product_input.text().strip()
        if not codigo_o_nombre:
            return
        
        print(f"Procesando entrada: {codigo_o_nombre}")

        # Parsear el código de barras para determinar si es un producto a peso variable
        info_producto = parsear_codigo_producto(codigo_o_nombre)
        
        if info_producto["tipo"] == "peso_variable":
            # Es un producto a peso variable
            codigo_producto = info_producto["codigo_producto"]
            peso_kg = info_producto["peso_kg"]
            
            print(f"Buscando producto con código base: {codigo_producto}")
            
            # Buscar el producto por su código
            producto = obtener_producto_por_codigo(codigo_producto)
            
            if producto:
                print(f"Producto encontrado: {producto[2]}, agregando con peso: {peso_kg}kg")
                # Agregar el producto con el peso leído del código de barras
                self.agregar_producto_con_peso(producto, peso_kg)
            else:
                QMessageBox.warning(self, "Producto no encontrado", f"No se encontró un producto con el código {codigo_producto}.")
        else:
            # Es un producto unitario o búsqueda por nombre
            print("Procesando como producto unitario o búsqueda por nombre")
            self.agregar_producto()
        
        # Limpiar el campo de entrada después de procesar
        self.product_input.clear()
    
    def agregar_producto_con_peso(self, producto, peso_kg):
        """Agrega un producto con un peso específico leído del código de barras"""
        id, codigo, nombre, precio_costo, precio_venta, margen_ganancia, venta_por_peso, disponible = producto[:8]
        
        # Verificar si hay suficiente stock disponible
        if peso_kg > disponible:
            QMessageBox.warning(self, "Error", f"No hay suficiente stock disponible para este producto. Disponible: {disponible:.3f}kg, Solicitado: {peso_kg:.3f}kg")
            logging.error(f"No hay suficiente stock disponible. Disponible: {disponible:.3f}kg, Solicitado: {peso_kg:.3f}kg")
            return
        
        # Desconectar la señal antes de modificar la tabla
        self.table.itemChanged.disconnect(self.actualizar_cantidad_producto)
        
        # Calcular el precio total
        precio_total = peso_kg * precio_venta
        
        # Añadir el producto a la tabla
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(codigo))
        self.table.setItem(row, 1, QTableWidgetItem(nombre))
        self.table.setItem(row, 2, QTableWidgetItem(f"{peso_kg:.3f}"))  # Mostrar el peso con 3 decimales
        self.table.setItem(row, 3, QTableWidgetItem(f"${precio_total:.2f}"))
        
        self.table.item(row, 2).setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        
        # Agregar el producto al carrito
        self.lista_productos.append((id, peso_kg, precio_total))
        self.total += precio_total
        self.actualizar_total()
        
        logging.info(f"Producto agregado por peso (código de barras): {nombre}, peso: {peso_kg:.3f}kg, precio: ${precio_total:.2f}")
        
        # Reconectar la señal después de modificar la tabla
        self.table.itemChanged.connect(self.actualizar_cantidad_producto)
    
    def agregar_producto(self):
        codigo_o_nombre = self.product_input.text().strip()
        logging.debug(f"Intentando agregar producto: {codigo_o_nombre}")
        
        producto = obtener_producto_por_codigo(codigo_o_nombre)
        
        if not producto:
            QMessageBox.warning(self, "Producto no encontrado", "No se encontró un producto con el código o nombre proporcionado.")
            logging.warning("Producto no encontrado.")
            return

        # Asegúrate de que el producto tenga la cantidad esperada de elementos
        if len(producto) < 8:
            QMessageBox.warning(self, "Error", "El producto no tiene la información completa.")
            logging.error("El producto no tiene la información completa.")
            return

        id, codigo, nombre, precio_costo, precio_venta, margen_ganancia, venta_por_peso, disponible = producto[:8]

        # Verificar si hay suficiente stock disponible
        if venta_por_peso == 0:  # Producto vendido por unidad
            dialog = CustomInputDialog(f"Ingrese la cantidad para {nombre}:")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    cantidad_a_vender = int(dialog.get_value())
                    if cantidad_a_vender <= 0:
                        QMessageBox.warning(self, "Error", "Cantidad inválida")
                        return
                except ValueError as e:
                    QMessageBox.warning(self, "Valor inválido", str(e))
        else:
            # Aquí se abre el diálogo para ingresar el peso
            dialog = CustomInputDialog(f"Ingrese el peso en kilogramos para {nombre}:")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    peso = float(dialog.get_value())
                    if peso <= 0:
                        QMessageBox.warning(self, "Error", "Peso inválido")
                        return
                    
                    cantidad_a_vender = peso  # Guardar el peso como cantidad

                except ValueError as e:
                    QMessageBox.warning(self, "Valor inválido", str(e))
                    logging.error(f"Error al ingresar peso: {e}")
                    return
            else:
                return
        if cantidad_a_vender > disponible:
            QMessageBox.warning(self, "Error", "No hay suficiente stock disponible para este producto.")
            logging.error("No hay suficiente stock disponible.")
            return

        # Desconectar la señal antes de modificar la tabla
        self.table.itemChanged.disconnect(self.actualizar_cantidad_producto)

        # Si el producto se vende por unidad, agregar directamente con cantidad 1
        if venta_por_peso == 0:  # 0 significa que se vende por unidad
            # Comprobar si el producto ya está en la lista de productos agregados
            for i, (prod_id, cantidad_existente, precio_total_existente) in enumerate(self.lista_productos):
                if prod_id == id:
                    # Producto ya existe, entonces vamos a sumar la cantidad
                    nueva_cantidad = cantidad_existente + cantidad_a_vender  # Aumentar la cantidad en 1
                    nuevo_precio_total = nueva_cantidad * precio_venta
                    
                    # Actualizar en la tabla y en la lista de productos
                    self.lista_productos[i] = (id, nueva_cantidad, nuevo_precio_total)
                    self.table.item(i, 2).setText(str(nueva_cantidad))
                    self.table.item(i, 3).setText(f"${nuevo_precio_total:.2f}")
                    
                    # Actualizar el total de la venta
                    self.total += precio_venta
                    self.actualizar_total()
                    self.product_input.clear()  # Limpiar el campo de entrada
                    logging.info(f"Producto actualizado: {nombre}, nueva cantidad: {nueva_cantidad}")
                    
                    # Reconectar la señal después de modificar la tabla
                    self.table.itemChanged.connect(self.actualizar_cantidad_producto)
                    return  # Salir del método para evitar duplicados

            # Si el producto no estaba en la lista, se añade normalmente
            cantidad = cantidad_a_vender  # Asignar cantidad 1 directamente
            precio_total = cantidad * precio_venta

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
            self.total += precio_total  # Solo sumar el precio total del nuevo producto
            self.actualizar_total()
            self.product_input.clear()  # Limpiar el campo de entrada
            logging.info(f"Producto agregado: {nombre}, cantidad: {cantidad}")
        else:
            # Si el producto se vende por peso, ya se maneja en la parte anterior
            precio_total = cantidad_a_vender * precio_venta

            # Añadir el nuevo producto a la tabla
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(codigo))
            self.table.setItem(row, 1, QTableWidgetItem(nombre))
            self.table.setItem(row, 2, QTableWidgetItem(str(cantidad_a_vender)))  # Editable
            self.table.setItem(row, 3, QTableWidgetItem(f"${precio_total:.2f}"))
            
            self.table.item(row, 2).setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)

            # Agregar el producto al carrito
            self.lista_productos.append((id, cantidad_a_vender, precio_total))
            self.total += precio_total  # Solo sumar el precio total del nuevo producto
            self.actualizar_total()
            self.product_input.clear()  # Limpiar el campo de entrada
            logging.info(f"Producto agregado por peso: {nombre}, cantidad: {cantidad_a_vender}")

        # Reconectar la señal después de modificar la tabla
        self.table.itemChanged.connect(self.actualizar_cantidad_producto)
    
    def actualizar_cantidad_producto(self, item: QTableWidgetItem):
        # Verifica si el cambio ocurre en la columna "Cantidad" (columna 2)
        if item.column() == 2:
            try:
                # Obtener el índice de la fila modificada
                row = item.row()

                # Validar si la fila corresponde a un índice válido en lista_productos
                if row < 0 or row >= len(self.lista_productos):
                    logging.error("Índice de fila fuera de rango al actualizar cantidad.")
                    self.product_input.clear()
                    return

                # Obtener detalles del producto desde la lista
                producto_id, cantidad_anterior, precio_total_anterior = self.lista_productos[row]
                producto = obtener_producto_por_id(producto_id)

                if not producto:
                    logging.error(f"No se encontró el producto con ID {producto_id} al actualizar cantidad.")
                    self.product_input.clear()
                    return
                stock_disponible = producto[7]
                print(f"Producto en índice 6: {producto[6]}")
                if (producto[6] == 1):
                    nueva_cantidad = float(item.text().strip())
                else:
                    nueva_cantidad = int(item.text().strip())  # Asegúrate de que sea un entero

                if nueva_cantidad <= 0:
                    QMessageBox.warning(self, "Error", "La cantidad debe ser mayor a 0.")
                    return


                if nueva_cantidad > stock_disponible:
                    QMessageBox.warning(self, "Stock Insuficiente", f"No hay suficiente stock para el producto. Disponible: {int(stock_disponible)}, Solicitado: {nueva_cantidad}.")
                    # Restaurar el valor anterior en la celda
                    self.table.item(row, 2).setText(str(cantidad_anterior))  # Columna 2: Cantidad
                    item.setText(str(cantidad_anterior))  # Restaurar el valor en el QTableWidgetItem
                    return

                # Calcular precio unitario y nuevo precio total
                precio_unitario = precio_total_anterior / cantidad_anterior
                nuevo_precio_total = nueva_cantidad * precio_unitario

                # Actualizar la lista de productos
                self.lista_productos[row] = (producto_id, nueva_cantidad, nuevo_precio_total)

                # Actualizar la tabla
                self.table.item(row, 3).setText(f"${nuevo_precio_total:.2f}")  # Columna 3: Precio total

                # Actualizar el total general
                self.total = sum(p[2] for p in self.lista_productos)
                self.actualizar_total()

            except ValueError as e:
                QMessageBox.warning(self, "Cantidad inválida", str(e))
                logging.error(f"Error al actualizar cantidad: {e}")
                # Restaurar el valor anterior en la celda
                self.table.item(row, 2).setText(str(cantidad_anterior))  # Columna 2: Cantidad
                item.setText(str(cantidad_anterior))  # Restaurar el valor en el QTableWidgetItem

            except IndexError as e:
                logging.error(f"Error de índice: {e}")
                # Actualizar el total general
                self.total = sum(p[2] for p in self.lista_productos)
                self.actualizar_total()


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
        self.payment_method.setCurrentIndex(0)  # Selecciona el primer elemento ("Efectivo")
    
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
                    ruta_ticket = self.generar_ticket(venta_id, self.lista_productos, self.total, metodo_pago, vuelto, monto_pagado)
                    if ruta_ticket:
                        if self.imprimir_ticket(ruta_ticket):
                            QMessageBox.information(self, "Ticket impreso", "El ticket se ha impreso correctamente.")
                        else:
                            QMessageBox.information(self, "Error", "No se pudo imprimir el ticket.")
                                
                QMessageBox.information(self, "Venta registrada", "La venta se ha registrado correctamente.")
                
                # Verificar stock restante
                try: # Add try-except block for robustness
                    for producto_id, _, _ in self.lista_productos: # Iterate through products sold
                        logging.debug(f"Verificando stock post-venta para producto ID: {producto_id} usando PostgreSQL.")
                        # Use the existing function to get product details from PostgreSQL
                        producto_actualizado = obtener_producto_por_id(producto_id)

                        if producto_actualizado is None:
                            logging.error(f"Producto ID {producto_id} no encontrado en PostgreSQL durante la verificación de stock post-venta.")
                            continue # Skip if product somehow not found

                        # Assuming index 7 is stock ('disponible') and index 2 is 'nombre'
                        # Adjust indices if your db_postgres functions return differently
                        if len(producto_actualizado) > 7:
                            stock_restante = producto_actualizado[7]
                            nombre = producto_actualizado[2]

                            # Ensure stock_restante is comparable (e.g., convert Decimal to float/int if needed)
                            try:
                                # Example: Convert if stock_restante might be Decimal
                                from decimal import Decimal
                                if isinstance(stock_restante, Decimal):
                                    stock_restante_num = float(stock_restante) # Or int() if always whole numbers
                                else:
                                    stock_restante_num = float(stock_restante) # Assume it can be float/int already
                            except (ValueError, TypeError) as conv_err:
                                logging.error(f"Error convirtiendo stock restante '{stock_restante}' para producto '{nombre}' (ID: {producto_id}): {conv_err}")
                                continue # Skip this product if conversion fails

                            logging.debug(f"Stock restante para '{nombre}' (ID: {producto_id}): {stock_restante_num}")

                            # Check if stock is low (e.g., <= 5)
                            if stock_restante_num <= 5:
                                logging.warning(f"Alerta de Stock Bajo para '{nombre}'. Restante: {stock_restante_num}")
                                QMessageBox.warning(self, "Alerta de Stock Bajo", f"El stock del producto {nombre} es bajo. Restante: {stock_restante_num:.2f}.") # Format as needed
                        else:
                            logging.warning(f"Datos incompletos recibidos de obtener_producto_por_id para ID {producto_id}. No se pudo verificar stock.")

                except Exception as e:
                    logging.exception("Error durante la verificación de stock post-venta:")
                    QMessageBox.critical(self, "Error", f"Ocurrió un error al verificar el stock restante: {e}")
                # --- Fin de la corrección ---
                
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
        ruta_ticket_absoluta = os.path.abspath(ruta_ticket)  # Obtener la ruta absoluta
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(ruta_ticket)

        # Márgenes y ancho útil
        MARGEN_HORIZONTAL = 10
        ANCHO_TICKET = 50 * mm
        ANCHO_UTIL = ANCHO_TICKET - (2 * MARGEN_HORIZONTAL)

        # Calcular el número de líneas necesario
        lineas = 13 # Encabezado, separadores y detalles finales
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
        ALTURA_TICKET = (lineas * 10) + 20

        # Crear el canvas con altura dinámica
        pdf = canvas.Canvas(ruta_ticket, pagesize=(ANCHO_TICKET, ALTURA_TICKET))

        # Configuración inicial del ticket
        y_position = ALTURA_TICKET - 10  # Margen superior
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "KIOSCO 25")
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

        if metodo_pago == "Efectivo":
            y_position -= 10
            pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Su pago: ${monto_pagado:.2f}")
            y_position -= 10
            pdf.drawString(MARGEN_HORIZONTAL, y_position, f"Vuelto: ${vuelto:.2f}")
            y_position -= 15
        else:
            y_position -=15
            
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "Gracias por su compra")
        y_position -= 10
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "=" * 30)
        pdf.setFont("Helvetica-Oblique", 8)
        y_position -= 10
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "*NO VÁLIDO COMO FACTURA*")
        y_position -= 10
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(ANCHO_TICKET / 2, y_position, "=" * 30)
        y_position -= 10

        # Guardar el archivo PDF
        pdf.save()
                        
        QMessageBox.information(self, "Ticket Generado", f"El ticket de venta ha sido guardado en {ruta_ticket}")

        return ruta_ticket_absoluta  # Retornar la ruta absoluta    
        

    def imprimir_ticket(self, ruta_ticket):
        # Imprimir el ticket usando la impresora predeterminada
        try:
            if os.path.exists(ruta_ticket):  # Verificar que el archivo existe
                win32api.ShellExecute(0, "print", ruta_ticket, None, ".", 0)
                return True  # Impresión exitosa
            else:
                QMessageBox.warning(self, "Error", "El archivo del ticket no existe.")
                return False  # Archivo no encontrado
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo imprimir el ticket: {e}")
            return False  # Error en la impresión
    
    
    def agregar_lote_a_venta(self, info_lote):
        """Agrega un lote específico a la venta actual"""
        producto_id = info_lote['producto_id']
        lote_id = info_lote['lote_id']
        nombre = info_lote['nombre']
        peso = info_lote['peso']
        # Asegúrate de que obtener_lote_por_codigo_barras devuelva 'precio_venta'
        precio_unitario = info_lote.get('precio_venta', 0) # Obtener precio_venta o default a 0
        if precio_unitario == 0:
             # Si no vino en info_lote, buscarlo en la tabla productos
             producto_db = obtener_producto_por_id(producto_id)
             if producto_db:
                 precio_unitario = producto_db[4] # Asumiendo que el índice 4 es precio_venta

        precio_total = peso * precio_unitario
        codigo_unico = info_lote['codigo_unico']

        print(f"Agregando Lote a Venta: ID={lote_id}, ProdID={producto_id}, Peso={peso}, PrecioU={precio_unitario}, PrecioT={precio_total}")

        # Necesitas una función que agregue a la tabla y guarde la info del lote
        self.agregar_item_a_tabla_ventas(
            producto_id=producto_id,
            nombre=f"{nombre} (Lote #{codigo_unico})",
            cantidad=1, # Para lotes, la cantidad es 1 (el lote entero)
            precio_unitario=precio_unitario, # Precio por KG
            precio_total=precio_total, # Precio total del lote
            lote_id=lote_id,
            peso=peso # Guardamos el peso del lote
        )

    # Add or ensure this method exists (crucial for storing batch info)
    def agregar_item_a_tabla_ventas(self, producto_id, nombre, cantidad, precio_unitario, precio_total, lote_id=None, peso=None):
        """Agrega un item a la tabla de ventas con soporte opcional para lotes y peso."""
        # Desconectar señal para evitar recursión o llamadas inesperadas
        try:
            self.table.itemChanged.disconnect(self.actualizar_cantidad_producto)
        except TypeError:
            pass # Ya estaba desconectada

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Crear items
        item_codigo = QTableWidgetItem(str(producto_id)) # Usar ID como código interno
        item_nombre = QTableWidgetItem(nombre)
        # Mostrar cantidad o peso formateado
        if peso is not None:
            item_cantidad = QTableWidgetItem(f"{peso:.3f} kg")
            # Hacer la celda de cantidad no editable para pesos/lotes
            item_cantidad.setFlags(item_cantidad.flags() & ~Qt.ItemFlag.ItemIsEditable)
        else:
            item_cantidad = QTableWidgetItem(str(cantidad))
            # Permitir edición para productos unitarios
            item_cantidad.setFlags(item_cantidad.flags() | Qt.ItemFlag.ItemIsEditable)

        item_precio_unitario = QTableWidgetItem(f"${precio_unitario:.2f}")
        item_precio_total = QTableWidgetItem(f"${precio_total:.2f}")

        # Añadir items a la tabla
        self.table.setItem(row, 0, item_codigo) # Columna 0: ID Producto
        self.table.setItem(row, 1, item_nombre) # Columna 1: Nombre (con info lote si aplica)
        self.table.setItem(row, 2, item_cantidad) # Columna 2: Cantidad o Peso
        self.table.setItem(row, 3, item_precio_total) # Columna 3: Precio Total

        # --- Almacenamiento de datos importantes ---
        # Guardar ID de producto real en UserRole del item de código/ID
        item_codigo.setData(Qt.ItemDataRole.UserRole, producto_id)

        # Guardar info de lote y peso en UserRole del item de cantidad/peso
        lote_data = {}
        if lote_id is not None:
            lote_data['lote_id'] = lote_id
        if peso is not None:
            lote_data['peso'] = peso
        # Guardar también si es unitario para diferenciar en registrar_venta
        lote_data['es_lote_o_peso'] = (lote_id is not None or peso is not None)
        lote_data['precio_unitario'] = precio_unitario # Guardar precio unitario para recálculos si es necesario

        item_cantidad.setData(Qt.ItemDataRole.UserRole, lote_data if lote_data else None)
        # -----------------------------------------

        # Actualizar total y limpiar entrada
        self.actualizar_total_venta() # Renombrar si es necesario
        self.product_input.clear()

        # Reconectar la señal
        self.table.itemChanged.connect(self.actualizar_cantidad_producto)
